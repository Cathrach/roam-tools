#######################################
# A converter from Roam's markdown to LaTeX, highly inspired by roam2tex.js
# 
# Meant for mostly mathematical work where I expect copious use of environments
# 
# Replaces markup (bold, italics, highlight) and hyperlinks, which use hyperref
# inserts citations in place of Roam page links ala roam2tex.js
#
# environments delineated using \begin{environment} and indenting; environments are automatically closed.
# enumerate and itemize environments will automatically \item only the blocks one indent level after them.
# all environments can be nested.
# equations are LaTeX on their own line, automatically placed into equation* environment. inline LaTeX is converted accordingly.
# refs are not supported yet! But it would be great to add support for block refs when Roam exports properly.
# customizable preamble and indent size (if your Roam exporting is weird, I don't expect this to be used)
# 
# usage: roam2tex.py infile_name [-o outfile_name] [-p preamble] [-i indent_size]
# if outfile_name is not given, outfile is infile + .tex
#
# Serina Hu (github.com/Cathrach)
# License: WTFPL
#######################################

import re
import argparse
import os

def render_citation(link_match):
    link_text = link_match.group(1)
    if not re.match(r"^[a-zA-Z]+[0-9]+[a-zA-Z]*$", link_text):
        return link_text
    
    return "\\cite{link_text}"
   

def replace_markup_via(text, delims, fun):
    chunks = text.split(delims)
    for i in range(1, len(chunks), 2):
        chunks[i] = fun(chunks[i])
    return "".join(chunks)
    
def convert_to_tex(infile_name, outfile_name, preamble, indent_size, ignore_properties):
    infile = open(infile_name, "r")
    outfile = open(outfile_name, "w")
    outfile.write(preamble)
    # TODO: make properties additional commands in the preamble
    outfile.write("\\begin{document}")
    # track indent levels for sections and paragraphs
    section_indent = None
    par_indent = None
    # track enumeration
    environments = []
    enum_indents = []
    
    for line in infile:
        # remove indentations and markdown bullets
        indent = len(re.match(r" *", line).group())
        line = re.sub(r"^ *(- )?", "", line)
        
        # skip any lines corresponding to properties we want to ignore
        if line.startswith(tuple([f"{s}::" for s in ignore_properties])):
            line = ""

        # skip any {{ functions
        line = re.sub(r"^\{\{(.+?)\}\}", "", line)
            
        # indentation management
        is_section = re.search(r"^#", line) is not None
        if is_section:
            section_indent = indent
            par_indent = None
        elif par_indent is None:
            # corresponds to previous line being a section header or no header
            par_indent = indent
            
        # close any active environments (which would only happen if we went back in indent, but whatever)
        # enumerate backwards over the `environments` list until we have closed everything appropriate
        length = len(environments)
        add_text = ""
        for i, (ind, env) in enumerate(environments[::-1]):
            if indent <= ind:
                add_text += f"\\end{{{env}}}\n"
                environments.pop(length - i - 1)
                if env in ["enumerate", "itemize"]:
                    enum_indents.remove(ind + indent_size)
            else:
                break
        
        if indent <= par_indent:
            add_text += "\n"
            par_indent = indent
    
        # turn section headings into section, subsection, subsubsection
        line = re.sub(r"^# (.*)", lambda m : f"\n\\section{{{m.group(1)}}}", line)
        line = re.sub(r"^## (.*)", lambda m : f"\n\\subsection{{{m.group(1)}}}", line)
        line = re.sub(r"^### (.*)", lambda m : f"\n\\subsubsection{{{m.group(1)}}}", line)
        
        # check if the line begins an environment
        env_begin = re.match(r"\\begin\{(.*?)\}", line)
        if env_begin:
            environment = env_begin.group(1)
            environments.append((indent, environment))
            if environment in ["enumerate", "itemize"]:
                enum_indents.append(indent + indent_size)
                
        # replace latex equations
        latex_eq = re.match(r"^\$\$([^$]*?)\$\$$", line)
        if latex_eq:
            line = f"\\begin{{equation*}}\n{latex_eq.group(1)}\n\\end{{equation*}}"
        else:
            # replace markup
            line = replace_markup_via(line, "__", lambda t : f"\\emph{{{t}}}")
            line = replace_markup_via(line, "**", lambda t : f"\\textbf{{{t}}}")
            line = replace_markup_via(line, "^^", lambda t : f"\\hl{{{t}}}")
            # replace inline latex
            line = line.replace("$$", "$")
            # replace Roam links
            line = re.sub(r"\[\[(.*?)\]\]", render_citation, line)
            # replace inline links
            line = re.sub(r"\[(.*?)\]\((.*)\)", lambda m : f"\\href{{{m.group(2)}}}{{{m.group(1)}}}", line)
            
            if indent in enum_indents:
                line = "\\item " + line
            
        line = add_text + line
            
        outfile.write(line + "\n")
    
    if environments != []:
        outfile.write("\n".join([f"\\end{{{env}}}\n" for _, env in environments[::-1]]))
        
    outfile.write("\n\\end{document}")
    
    infile.close()
    outfile.close()
    


def main():
    default_preamble = "\\documentclass[12pt]{article}\n\\usepackage{serina}\n"

    parser = argparse.ArgumentParser()
    parser.add_argument("infile", help="name of input file")
    parser.add_argument("-o", "--outfile", help="name of output file if different from input")
    parser.add_argument("-i", "--indent-size", help="number of spaces in indent", default=4)
    parser.add_argument("-p", "--preamble", help="preamble for document", default=default_preamble)
    args = parser.parse_args()

    infile_name = args.infile
    outfile_name = args.outfile if args.outfile is not None else os.path.splitext(infile_name)[0] + ".tex"
    indent_size = args.indent_size
    preamble = args.preamble
    ignore_properties = ["tags", "do", "due"] #TODO: make this an option
    
    convert_to_tex(infile_name, outfile_name, preamble, indent_size, ignore_properties)
    
if __name__ == "__main__":
    main()
