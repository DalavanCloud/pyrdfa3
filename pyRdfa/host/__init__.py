# -*- coding: utf-8 -*-
"""
Host language sub-package for the pyRdfa package. It contains variables and possible modules necessary to manage various RDFa
host languages.

This module may have to be modified if a new host language is added to the system. In many cases the rdfa_core as a host language is enough, because there is no need for a special processing. However, some host languages may require an initial context, or their value may control some transformations, in which case additional data have to be added to this module. This module header contains all tables and arrays to be adapted, and the module content may contain specific transformation methods.


@summary: RDFa Host package
@requires: U{RDFLib package<http://rdflib.net>}
@organization: U{World Wide Web Consortium<http://www.w3.org>}
@author: U{Ivan Herman<a href="http://www.w3.org/People/Ivan/">}
@license: This software is available for use under the
U{W3C® SOFTWARE NOTICE AND LICENSE<href="http://www.w3.org/Consortium/Legal/2002/copyright-software-20021231">}

@var content_to_host_language: a dictionary mapping a media type to a host language
@var preferred_suffixes: mapping from preferred suffixes for media types; used if the file is local, ie, there is not HTTP return value for the media type. It corresponds to the preferred suffix in the media type registration
@var initial_contexts: mapping from host languages to list of initial contexts
@var accept_xml_base: list of host languages that accept the xml:base attribute for base setting
@var accept_xml_lang: list of host languages that accept the xml:lang attribute for language setting. Note that XHTML and HTML have some special rules, and those are hard coded...
@var accept_embedded_rdf_xml: list of host languages that might also include RDF data using an embedded RDF/XML (e.g., SVG). That RDF data may be merged with the output
@var accept_embedded_turtle: list of host languages that might also include RDF data using a C{script} element. That RDF data may be merged with the output
@var host_dom_transforms: dictionary mapping a host language to an array of methods that are invoked at the beginning of the parsing process for a specific node. That function can do a last minute change on that DOM node, eg, adding or modifying an attribute. The method's signature is (node, state), where node is the DOM node, and state is the L{Execution context<pyRdfa.state.ExecutionContext>}.
@var predefined_1_0_rel: terms that are hardcoded for HTML+RDF1.0 and replace the initial context for that version
@var beautifying_prefixes: this is really just to make the output more attractive: for each media type a dictionary of prefix-URI pairs that can be used to make the terms look better...
"""

"""
$Id: __init__.py,v 1.11 2012-03-23 14:06:31 ivan Exp $
$Date: 2012-03-23 14:06:31 $
"""
__version__ = "3.0"

from pyRdfa.host.atom  import atom_add_entry_type
from pyRdfa.host.html5 import html5_extra_attributes

class HostLanguage :
	"""An enumeration style class: recognized host language types for this processor of RDFa. Some processing details may depend on these host languages. "rdfa_core" is the default Host Language is nothing else is defined."""
	rdfa_core 	= "RDFa Core"
	xhtml		= "XHTML+RDFa"
	xhtml5		= "XHTML5+RDFa"
	html5		= "HTML5+RDFa"
	atom		= "Atom+RDFa"
	svg			= "SVG+RDFa"
	
# initial contexts for host languages
initial_contexts = {
	HostLanguage.xhtml		: ["http://www.w3.org/2011/rdfa-context/rdfa-1.1",
							   "http://www.w3.org/2011/rdfa-context/xhtml-rdfa-1.1"],
	HostLanguage.xhtml5		: ["http://www.w3.org/2011/rdfa-context/rdfa-1.1"],
	HostLanguage.html5 		: ["http://www.w3.org/2011/rdfa-context/rdfa-1.1"],
	HostLanguage.rdfa_core 	: ["http://www.w3.org/2011/rdfa-context/rdfa-1.1"],
	HostLanguage.atom	 	: ["http://www.w3.org/2011/rdfa-context/rdfa-1.1"],
	HostLanguage.svg	 	: ["http://www.w3.org/2011/rdfa-context/rdfa-1.1"],
}

beautifying_prefixes = {
	HostLanguage.xhtml	: {
		"xhv" : "http://www.w3.org/1999/xhtml/vocab#"
	},
	HostLanguage.html5	: {
		"xhv" : "http://www.w3.org/1999/xhtml/vocab#"
	},	
	HostLanguage.xhtml5	: {
		"xhv" : "http://www.w3.org/1999/xhtml/vocab#"
	},	
}


accept_xml_base		= [ HostLanguage.rdfa_core, HostLanguage.atom, HostLanguage.svg ]
accept_xml_lang		= [ HostLanguage.rdfa_core, HostLanguage.atom, HostLanguage.svg ]

accept_embedded_rdf_xml	= [ HostLanguage.svg, HostLanguage.rdfa_core ]
accept_embedded_turtle	= [ HostLanguage.svg, HostLanguage.html5, HostLanguage.xhtml5, HostLanguage.xhtml ]

host_dom_transforms = {
	HostLanguage.atom   : [atom_add_entry_type],
	HostLanguage.html5  : [html5_extra_attributes],
	HostLanguage.xhtml5 : [html5_extra_attributes]
}

predefined_1_0_rel  = ['alternate', 'appendix', 'cite', 'bookmark', 'chapter', 'contents',
'copyright', 'glossary', 'help', 'icon', 'index', 'meta', 'next', 'p3pv1', 'prev', 'previous', 
'role', 'section', 'subsection', 'start', 'license', 'up', 'last', 'stylesheet', 'first', 'top']

# ----------------------------------------------------------------------------------------------------------
		
class MediaTypes :
	"""An enumeration style class: some common media types (better have them at one place to avoid misstyping...)"""
	rdfxml 	= 'application/rdf+xml'
	turtle 	= 'text/turtle'
	html	= 'text/html'
	xhtml	= 'application/xhtml+xml'
	svg		= 'application/svg+xml'
	smil	= 'application/smil+xml'
	atom	= 'application/atom+xml'
	xml		= 'application/xml'
	xmlt	= 'text/xml'
	nt		= 'text/plain'
	
# mapping from (some) content types to RDFa host languages. This may control the exact processing or at least the initial context (see below)...
content_to_host_language = {
	MediaTypes.html		: HostLanguage.html5,
	MediaTypes.xhtml	: HostLanguage.xhtml,
	MediaTypes.xml		: HostLanguage.rdfa_core,
	MediaTypes.xmlt		: HostLanguage.rdfa_core,
	MediaTypes.smil		: HostLanguage.rdfa_core,
	MediaTypes.svg		: HostLanguage.svg,
	MediaTypes.atom		: HostLanguage.atom,
}

# mapping preferred suffixes to media types...
preferred_suffixes = {
	".rdf"		: MediaTypes.rdfxml,
	".ttl"		: MediaTypes.turtle,
	".n3"		: MediaTypes.turtle,
	".owl"		: MediaTypes.rdfxml,
	".html"		: MediaTypes.html,
	".xhtml"	: MediaTypes.xhtml,
	".svg"		: MediaTypes.svg,
	".smil"		: MediaTypes.smil,
	".xml"		: MediaTypes.xml,
	".nt"		: MediaTypes.nt,
	".atom"		: MediaTypes.atom
}
	
	
def adjust_xhtml(dom, incoming_language) :
	"""
	Check if the xhtml+RDFa is really XHTML 0 or 1 or whether it should be considered as XHTML5. This is done
	by looking at the DTD...
	@param dom: top level DOM node
	@param incoming_language: host language to be checked; the whole check is relevant for xhtml only.
	@return: possibly modified host language (ie, set to XHTML5)
	"""
	pids = ["-//W3C//DTD XHTML+RDFa 1.1//EN",
			"-//W3C//DTD XHTML+RDFa 1.0//EN",
			"-//W3C//DTD XHTML 1.0 Strict//EN",
			"-//W3C//DTD XHTML 1.0 Transitional//EN",
			"-//W3C//DTD XHTML 1.1//EN"
			]
	sids = ["http://www.w3.org/MarkUp/DTD/xhtml-rdfa-2.dtd",
			"http://www.w3.org/MarkUp/DTD/xhtml-rdfa-1.dtd",
			"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd",
			"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd",
			"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd"
			]
	if incoming_language == HostLanguage.xhtml :
		try :
			# There may not be any doctype set in the first place...
			publicId = dom.doctype.publicId
			systemId = dom.doctype.systemId
			if publicId in pids and systemId in sids :
				return HostLanguage.xhtml
			else :
				return HostLanguage.xhtml5
		except :
			# If any of those are missing, forget it...
			return HostLanguage.xhtml5
	else :
		return incoming_language

