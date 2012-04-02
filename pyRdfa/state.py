# -*- coding: utf-8 -*-
"""
Parser's execution context (a.k.a. state) object and handling. The state includes:

  - language, retrieved from C{@xml:lang}
  - URI base, determined by <base> (or set explicitly). This is a little bit superfluous, because the current RDFa syntax does not make use of C{@xml:base}; ie, this could be a global value.  But the structure is prepared to add C{@xml:base} easily, if needed.
  - options, in the form of an L{options<pyRdfa.options>} instance
  - a separate vocabulary/CURIE handling resource, in the form of an L{termorcurie<pyRdfa.TermOrCurie>} instance

The execution context object is also used to handle URI-s, CURIE-s, terms, etc.

@summary: RDFa parser execution context
@requires: U{RDFLib package<http://rdflib.net>}
@organization: U{World Wide Web Consortium<http://www.w3.org>}
@author: U{Ivan Herman<a href="http://www.w3.org/People/Ivan/">}
@license: This software is available for use under the
U{W3C® SOFTWARE NOTICE AND LICENSE<href="http://www.w3.org/Consortium/Legal/2002/copyright-software-20021231">}
"""

"""
$Id: state.py,v 1.4 2011/11/14 14:02:48 ivan Exp $
$Date: 2011/11/14 14:02:48 $
"""

import rdflib
from rdflib	import URIRef
from rdflib	import Literal
from rdflib	import BNode
from rdflib	import Namespace
if rdflib.__version__ >= "3.0.0" :
	from rdflib	import RDF  as ns_rdf
	from rdflib	import RDFS as ns_rdfs
else :
	from rdflib.RDFS	import RDFSNS as ns_rdfs
	from rdflib.RDF		import RDFNS  as ns_rdf

from pyRdfa.options		import Options
from pyRdfa.utils 		import quote_URI
from pyRdfa.host 		import HostLanguage, accept_xml_base, accept_xml_lang, beautifying_prefixes

from pyRdfa.termorcurie	import TermOrCurie
from pyRdfa				import UnresolvablePrefix, UnresolvableTerm

from pyRdfa import err_lang							
from pyRdfa import err_URI_scheme						
from pyRdfa import err_illegal_safe_CURIE				
from pyRdfa import err_no_CURIE_in_safe_CURIE			
from pyRdfa import err_undefined_terms					
from pyRdfa import err_non_legal_CURIE_ref				
from pyRdfa import err_undefined_CURIE					

import re
import random
import urlparse
import urllib
from types import *

class ListStructure :
	def __init__(self) :
		self.mapping = {}
		self.origin	  = None

#### Core Class definition
class ExecutionContext :
	"""State at a specific node, including the current set of namespaces in the RDFLib sense, current language,
	the base, vocabularies, etc. The class is also used to interpret URI-s and CURIE-s to produce
	URI references for RDFLib.
	
	@ivar options: reference to the overall options
	@type options: L{Options}
	@ivar base: the 'base' URI
	@ivar parsedBase: the parsed version of base, as produced by urlparse.urlsplit
	@ivar defaultNS: default namespace (if defined via @xmlns) to be used for XML Literals
	@ivar lang: language tag (possibly None)
	@ivar term_or_curie: vocabulary management class instance
	@type term_or_curie: L{termorcurie.TermOrCurie}
	@ivar list_mapping: dictionary of arrays, containing a list of URIs key-ed via properties for lists
	@ivar setting_subject: whether the element with that state sets the subject down the line via @resource or @href
	@ivar node: the node to which this state belongs
	@type node: DOM node instance
	@ivar rdfa_version: RDFa version of the content
	@type rdfa_version: String
	@cvar _list: list of attributes that allow for lists of values and should be treated as such
	@cvar _resource_type: dictionary; mapping table from attribute name to the exact method to retrieve the URI(s). Is initialized at first run
	"""

	# list of attributes that allow for lists of values and should be treated as such	
	_list = [ "rel", "rev", "property", "typeof" ]
	# mapping table from attribute name to the exact method to retrieve the URI(s).
	_resource_type = {}
	
	def __init__(self, node, graph, inherited_state=None, base="", options=None, rdfa_version = None) :
		"""
		@param node: the current DOM Node
		@param graph: the RDFLib Graph
		@keyword inherited_state: the state as inherited
		from upper layers. This inherited_state is mixed with the state information
		retrieved from the current node.
		@type inherited_state: L{state.ExecutionContext}
		@keyword base: string denoting the base URI for the specific node. This overrides the possible
		base inherited from the upper layers. The 
		current XHTML+RDFa syntax does not allow the usage of C{@xml:base}, but SVG1.2 does, so this is
		necessary for SVG (and other possible XML dialects that accept C{@xml:base})
		@keyword options: invocation options, and references to warning graphs
		@type options: L{Options<pyRdfa.options>}
		"""
		def remove_frag_id(uri) :
			"""
			The fragment ID for self.base must be removed
			"""
			try :
				# To be on the safe side:-)
				t = urlparse.urlparse(uri)
				return urlparse.urlunparse((t[0],t[1],t[2],t[3],t[4],""))
			except :
				return uri
			
		# This is, conceptually, an additional class initialization, but it must be done run time, otherwise import errors show up
		if len(	ExecutionContext._resource_type ) == 0 :	
			ExecutionContext._resource_type = {
				"href"		:	ExecutionContext._URI,
				"src"		:	ExecutionContext._URI,
				"vocab"	    :   ExecutionContext._URI,
			
				"about"		:	ExecutionContext._CURIEorURI, 
				"resource"	:	ExecutionContext._CURIEorURI, 
			
				"rel"		:	ExecutionContext._TERMorCURIEorAbsURI,
				"rev"		:	ExecutionContext._TERMorCURIEorAbsURI,
				"datatype"	:	ExecutionContext._TERMorCURIEorAbsURI,
				"typeof"	:	ExecutionContext._TERMorCURIEorAbsURI,
				"property"	:	ExecutionContext._TERMorCURIEorAbsURI,
			}	
		#-----------------------------------------------------------------
		self.node = node
		
		#-----------------------------------------------------------------
		# Settling the base. In a generic XML, xml:base should be accepted at all levels (though this is not the
		# case in, say, XHTML...)
		# At the moment, it is invoked with a 'None' at the top level of parsing, that is
		# when the <base> element is looked for (for the HTML cases, that is)
		if inherited_state :
			self.rdfa_version		= inherited_state.rdfa_version
			self.base				= inherited_state.base
			self.options			= inherited_state.options
						
			self.list_mapping 		= inherited_state.list_mapping
			self.new_list			= False
			
			# for generic XML versions the xml:base attribute should be handled
			if self.options.host_language in accept_xml_base and node.hasAttribute("xml:base") :
				self.base = remove_frag_id(node.getAttribute("xml:base"))
		else :
			# this is the branch called from the very top			
			self.list_mapping = ListStructure()
			self.new_list	  = True
			
			if rdfa_version is not None :
				self.rdfa_version = rdfa_version
			else :
				from pyRdfa import rdfa_current_version				
				self.rdfa_version = rdfa_current_version
				# This value can be overwritten by a @version attribute
				if node.hasAttribute("version") :
					top_version = node.getAttribute("version")
					if top_version.find("RDFa 1.0") != -1 :
						self.rdfa_version = "1.0"
					elif top_version.find("RDFa 1.1") != -1 :
						self.rdfa_version = "1.1"						
			
			# this is just to play safe. I believe this should actually not happen...
			if options == None :
				from pyRdfa import Options
				self.options = Options()
			else :
				self.options = options

			self.base = ""
			# handle the base element case for HTML
			if self.options.host_language in [ HostLanguage.xhtml, HostLanguage.html ] :
				for bases in node.getElementsByTagName("base") :
					if bases.hasAttribute("href") :
						self.base = remove_frag_id(bases.getAttribute("href"))
						continue
			elif self.options.host_language in accept_xml_base and node.hasAttribute("xml:base") :
				self.base = remove_frag_id(node.getAttribute("xml:base"))
				
			# If no local setting for base occurs, the input argument has it
			if self.base == "" :
				self.base = base
				
			# Perform an extra beautification in RDFLib
			if self.options.host_language in beautifying_prefixes :
				dict = beautifying_prefixes[self.options.host_language]
				for key in dict :
					graph.bind(key,dict[key])

								
		#-----------------------------------------------------------------
		# this will be used repeatedly, better store it once and for all...		
		self.parsedBase = urlparse.urlsplit(self.base)

		#-----------------------------------------------------------------
		# generate and store the local CURIE handling class instance
		self.term_or_curie = TermOrCurie(self, graph, inherited_state)

		#-----------------------------------------------------------------
		# Settling the language tags
		# @lang has priority over @xml:lang
		# it is a bit messy: the three fundamental modes (xhtml, html, or xml) are all slightly different:-(
		# first get the inherited state's language, if any
		if inherited_state :
			self.lang = inherited_state.lang
		else :
			self.lang = None
			
		if self.options.host_language in [ HostLanguage.xhtml, HostLanguage.html ] :
			# we may have lang and xml:lang
			if node.hasAttribute("lang") :
				lang = node.getAttribute("lang").lower()
			else :
				lang = None

			if node.hasAttribute("xml:lang") :
				xmllang = node.getAttribute("xml:lang").lower()
			else :
				xmllang = None
				
			# First of all, set the value, if any
			if xmllang != None :
				# this has priority
				if len(xmllang) != 0 :
					self.lang = xmllang
				else :
					self.lang = None
			elif lang != None :
				if len(lang) != 0 :
					self.lang = lang
				else :
					self.lang = None
				
			# check a posible warning (error?), too
			if lang != None and xmllang != None and lang != xmllang :
				self.options.add_warning(err_lang % (xmllang, lang), node=self.node.nodeName)
		else :
			# this is a clear case, xml:lang is the only possible option...
			if self.options.host_language in accept_xml_lang and node.hasAttribute("xml:lang") :
				self.lang = node.getAttribute("xml:lang").lower()
				if len(self.lang) == 0 : self.lang = None
			
		#-----------------------------------------------------------------
		# Set the default namespace. Used when generating XML Literals
		if node.hasAttribute("xmlns") :
			self.defaultNS = node.getAttribute("xmlns")
		elif inherited_state and inherited_state.defaultNS != None :
			self.defaultNS = inherited_state.defaultNS
		else :
			self.defaultNS = None
	# end __init__

	def _URI(self, val) :
		"""Returns a URI for a 'pure' URI (ie, not a CURIE). The method resolves possible relative URI-s. It also
		checks whether the URI uses an unusual URI scheme (and issues a warning); this may be the result of an
		uninterpreted CURIE...
		@param val: attribute value to be interpreted
		@type val: string
		@return: an RDFLib URIRef instance
		"""
		def create_URIRef(uri, check = True) :
			"""
			Mini helping function: it checks whether a uri is using a usual scheme before a URIRef is created. In case
			there is something unusual, a warning is generated (though the URIRef is created nevertheless)
			@param uri: (absolute) URI string
			@return: an RDFLib URIRef instance
			"""
			from pyRdfa	import uri_schemes
			val = uri.strip()
			if check and urlparse.urlsplit(val)[0] not in uri_schemes :
				self.options.add_warning(err_URI_scheme % val.strip(), node=self.node.nodeName)
			return URIRef(val)

		def join(base, v, check = True) :
			"""
			Mini helping function: it makes a urljoin for the paths. Based on the python library, but
			that one has a bug: in some cases it
			swallows the '#' or '?' character at the end. This is clearly a problem with
			Semantic Web URI-s, so this is checked, too
			@param base: base URI string
			@param v: local part
			@return: an RDFLib URIRef instance
			"""
			joined = urlparse.urljoin(base, v)
			try :
				if v[-1] != joined[-1] :
					return create_URIRef(joined + v[-1], check)
				else :
					return create_URIRef(joined, check)
			except :
				return create_URIRef(joined, check)

		if val == "" :
			# The fragment ID must be removed...
			return URIRef(self.base)
			

		# fall back on good old traditional URI-s.
		# To be on the safe side, let us use the Python libraries
		if self.parsedBase[0] == "" :
			# base is, in fact, a local file name
			# The following call is just to be sure that some pathological cases when
			# the ':' _does_ appear in the URI but not in a scheme position is taken
			# care of properly...
			
			key = urlparse.urlsplit(val)[0]
			if key == "" :
				# relative URI, to be combined with local file name:
				return join(self.base, val, check = False)
			else :
				return create_URIRef(val)
		else :
			# Trust the python library...
			# Well, not quite:-) there is what is, in my view, a bug in the urljoin; in some cases it
			# swallows the '#' or '?' character at the end. This is clearly a problem with
			# Semantic Web URI-s			
			return join(self.base, val)
	# end _URI

	def _CURIEorURI(self, val) :
		"""Returns a URI for a (safe or not safe) CURIE. In case it is a safe CURIE but the CURIE itself
		is not defined, an error message is issued. Otherwise, if it is not a CURIE, it is taken to be a URI
		@param val: attribute value to be interpreted
		@type val: string
		@return: an RDFLib URIRef instance or None
		"""
		if val == "" :
			return URIRef(self.base)

		safe_curie = False
		if val[0] == '[' :
			# If a safe CURIE is asked for, a pure URI is not acceptable.
			# Is checked below, and that is why the safe_curie flag is necessary
			if val[-1] != ']' :
				# that is certainly forbidden: an incomplete safe CURIE
				self.options.add_warning(err_illegal_safe_CURIE % val, UnresolvablePrefix, node=self.node.nodeName)
				return None
			else :
				val = val[1:-1]
				safe_curie = True
		# There is a branch here depending on whether we are in 1.1 or 1.0 mode
		if self.rdfa_version >= "1.1" :
			retval = self.term_or_curie.CURIE_to_URI(val)
			if retval == None :
				# the value could not be interpreted as a CURIE, ie, it did not produce any valid URI.
				# The rule says that then the whole value should be considered as a URI
				# except if it was part of a safe CURIE. In that case it should be ignored...
				if safe_curie :
					self.options.add_warning(err_no_CURIE_in_safe_CURIE % val, UnresolvablePrefix, node=self.node.nodeName)
					return None
				else :
					return self._URI(val)
			else :
				# there is an unlikely case where the retval is actually a URIRef with a relative URI. Better filter that one out
				if isinstance(retval, BNode) == False and urlparse.urlsplit(str(retval))[0] == "" :
					# yep, there is something wrong, a new URIRef has to be created:
					return URIRef(self.base+str(retval))
				else :
					return retval
		else :
			# in 1.0 mode a CURIE can be considered only in case of a safe CURIE
			if safe_curie :
				return self.term_or_curie.CURIE_to_URI(val)
			else :
				return self._URI(val)
	# end _CURIEorURI

	def _TERMorCURIEorAbsURI(self, val) :
		"""Returns a URI either for a term or for a CURIE. The value must be an NCNAME to be handled as a term; otherwise
		the method falls back on a CURIE or an absolute URI.
		@param val: attribute value to be interpreted
		@type val: string
		@return: an RDFLib URIRef instance or None
		"""
		from pyRdfa	import uri_schemes
		# This case excludes the pure base, ie, the empty value
		if val == "" :
			return None
		
		from termorcurie import ncname
		if ncname.match(val) :
			# This is a term, must be handled as such...
			retval = self.term_or_curie.term_to_URI(val)
			if not retval :
				self.options.add_warning(err_undefined_terms % val, UnresolvableTerm, node=self.node.nodeName)
				return None
			else :
				return retval
		else :
			# try a CURIE
			retval = self.term_or_curie.CURIE_to_URI(val)
			if retval :
				return retval
			elif self.rdfa_version >= "1.1" :
				# See if it is an absolute URI
				scheme = urlparse.urlsplit(val)[0]
				if scheme == "" :
					# bug; there should be no relative URIs here
					self.options.add_warning(err_non_legal_CURIE_ref % val, UnresolvablePrefix, node=self.node.nodeName)
					return None
				else :
					if scheme not in uri_schemes :
						self.options.add_warning(err_URI_scheme % val.strip(), node=self.node.nodeName)
					return URIRef(val)
			else :
				# rdfa 1.0 case
				self.options.add_warning(err_undefined_CURIE % val.strip(), UnresolvablePrefix, node=self.node.nodeName)
				return None
	# end _TERMorCURIEorAbsURI

	# -----------------------------------------------------------------------------------------------

	def getURI(self, attr) :
		"""Get the URI(s) for the attribute. The name of the attribute determines whether the value should be
		a pure URI, a CURIE, etc, and whether the return is a single element of a list of those. This is done
		using the L{ExecutionContext._resource_type} table.
		@param attr: attribute name
		@type attr: string
		@return: an RDFLib URIRef instance (or None) or a list of those
		"""
		if self.node.hasAttribute(attr) :
			val = self.node.getAttribute(attr)
		else :
			if attr in ExecutionContext._list :
				return []
			else :
				return None
		
		# This may raise an exception if the attr has no key. This, actually,
		# should not happen if the code is correct, but it does not harm having it here...
		try :
			func = ExecutionContext._resource_type[attr]
		except :
			# Actually, this should not happen...
			func = ExecutionContext._URI
		
		if attr in ExecutionContext._list :
			# Allows for a list
			resources = [ func(self, v.strip()) for v in val.strip().split() if v != None ]
			retval = [ r for r in resources if r != None ]
		else :
			retval = func(self, val.strip())
		return retval
	# end getURI
	
	def getResource(self, *args) :
		"""Get single resources from several different attributes. The first one that returns a valid URI wins.
		@param args: variable list of attribute names, or a single attribute being a list itself.
		@return: an RDFLib URIRef instance (or None) :
		"""
		if len(args) == 0 :
			return None
		if isinstance(args[0], (tuple,list)) :
			rargs = args[0]
		else :
			rargs = args
			
		for resource in rargs :
			uri = self.getURI(resource)
			if uri != None : return uri
		return None
	
	# -----------------------------------------------------------------------------------------------
	def reset_list_mapping(self, origin=None) :
		"""
		Reset, ie, create a new empty dictionary for the list mapping.
		"""
		self.list_mapping = ListStructure()
		if origin: self.set_list_origin(origin)
		self.new_list = True

	def list_empty(self) :
		return len(self.list_mapping.mapping) == 0
		
	def get_list_props(self) :
		return self.list_mapping.mapping.keys()
		
	def get_list_value(self,prop) :
		return self.list_mapping.mapping[prop]
		
	def set_list_origin(self, origin) :
		self.list_mapping.origin = origin
		
	def get_list_origin(self) :
		return self.list_mapping.origin
		
	def add_to_list_mapping(self, property, resource) :
		"""Add a new property-resource on the list mapping structure. The latter is a dictionary of arrays;
		if the array does not exist yet, it will be created on the fly.
		
		@param property: the property URI, used as a key in the dictionary
		@param resource: the resource to be added to the relevant array in the dictionary.
		"""
		if property in self.list_mapping.mapping :
			self.list_mapping.mapping[property].append(resource)
		else :
			self.list_mapping.mapping[property] = [ resource ]

####################
