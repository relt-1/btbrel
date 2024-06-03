import markdown2
import sys
import os
import re
import shutil

mark = markdown2.Markdown(extras={"tables":True,"fenced-code-blocks":None,"code-friendly":True,"break-on-newline":True,"markdown-in-html":True})

rootpath = os.path.dirname(os.path.realpath(__file__))
src = rootpath+"/src/"
lensrc = len(src)
dst = rootpath+"/dst/"
assets = rootpath+"/assets/"
if os.path.exists(dst):
    shutil.rmtree(dst)
shutil.copytree(assets,dst)
with open("template.html","r") as f:
    template = f.read()

documentlist = []
namelist = []
filetreedict = {}
filetree = ""

for root, subdirs, files in os.walk(src):
    p = filetreedict
    if root[lensrc:]:
        for x in root[lensrc:].replace("\\","/").split("/"):
            p = p.setdefault(x, {})
    p[''] = []
    for file in files:
        if file.endswith(".embed.md"):
            continue
        fpath = os.path.join(root, file)
        with open(fpath,"r") as f:
            rawmarkdown = f.read()
            h1s = rawmarkdown.split("#")
            if(len(h1s) == 1):
                raise SyntaxError(".md file must begin with a # marked title!")
            name = h1s[1].split("\n",1)[0]
            p[''].append([os.path.join(root[lensrc:],file.replace(".md","")).replace("\\","/"),name])
            documentlist.append("/wiki/"+fpath[len(src):].replace(".md",".html").replace("\\","/"))
            namelist.append(name)

def IterateFileTree(filedict,path,parentexpanded):
    global filetree
    currentfile = path[1:].replace(".md","")
    for key, value in filedict.items():
        if isinstance(value, dict):
            classname = "nested"
            expandicon = "+"
            expanded = False
            if "/"+key+"/" in path and parentexpanded:
                classname += " active"
                expandicon = "-"
                expanded = True
            
            filetree += f"<li class=\"sidebar\"><small class=\"liicon\">{expandicon}</small><span onmousedown=\"toggleTree(this);\" onmouseleave=\"unPress(this);\" onmouseup=\"unPress(this);\"><span onmousedown=\"Press(this);\" onmouseleave=\"unPress(this);\" onmouseup=\"unPress(this);\">{key}</span></span>\n<ul class=\"sidebar {classname}\">\n"
            IterateFileTree(value,path,expanded)
            filetree += f"</ul>\n</li>\n"
        else:
            for file in value:
                if file[0] == currentfile:
                    filetree += f"<li class=\"sidebar\"><b>{file[1]}</b></li>\n"
                else:
                    filetree += f"<li class=\"sidebar\"><a href=\"/wiki/{file[0]}.html\">{file[1]}</a></li>\n"

def FindFile(name):
    for root, subdirs, files in os.walk(src):
        if name in files:
            return os.path.join(root[lensrc:],name)
    raise SyntaxError(f"Could not find file {name}!")


def ConvertStrToHtml(rawmarkdown : str):
    i = 0
    indentlevel = 0
    beginningdollar = -1
    tocut = -1
    dollarname = ""
    while True:
        if rawmarkdown[i:i+2] == '$_':
            if indentlevel == 0:
                tocut = i
                dollarsnippet = rawmarkdown[i+2:]
                if dollarsnippet.startswith("SMALL"):
                    dollarname = "SMALL"
                    i+=5
                elif dollarsnippet.startswith("FRAME"):
                    dollarname = "FRAME"
                    i+=5
                elif dollarsnippet.startswith("INLINEFRAME"):
                    dollarname = "INLINEFRAME"
                    i+=11
                elif dollarsnippet.startswith("COMMENT"):
                    dollarname = "COMMENT"
                    i+=7
                elif dollarsnippet.startswith("RIGHTFRAME"):
                    dollarname = "RIGHTFRAME"
                    i+=10
                elif dollarsnippet.startswith("BUTTON"):
                    dollarname = "BUTTON"
                    i+=6
                beginningdollar = i+2
            indentlevel += 1
            i+=2
        elif rawmarkdown[i:i+2] == "_$":
            indentlevel -= 1
            if indentlevel == 0 and beginningdollar != -1:
                snippet = ""
                if dollarname != "COMMENT":
                    snippet = ConvertStrToHtml(rawmarkdown[beginningdollar:i].strip()).strip()
                if dollarname == "SMALL":
                    snippet = "<small style=\"position:relative; top:8px; margin:0px;\">"+snippet.strip().replace("<p>","").replace("</p>","")+"</small>"
                elif dollarname == "FRAME":
                    snippet = "<div class=\"framed\"><div class=\"framedinside\">"+snippet+"</div></div>"
                elif dollarname == "RIGHTFRAME":
                    snippet = "<div class=\"rightframed\"><div class=\"rightframedinside\">"+snippet+"</div></div>"
                elif dollarname == "INLINEFRAME":
                    snippet = f"<div class=\"inlineframed\"><div class=\"inlineframedinside\">{snippet}</div></div>"
                elif dollarname == "BUTTON":
                    snippet = "<span class=\"buttoned\">"+snippet.strip().replace("<p>","").replace("</p>","")+"</span>"
                rawmarkdown = rawmarkdown[:tocut]+snippet+rawmarkdown[i+2:]
                beginningdollar = -1
                i = tocut+len(snippet)-3
            i+=2
        i+=1
        if i>len(rawmarkdown):
            break
    links = re.findall(r'\[\[[^\[^\]]+\]\]', rawmarkdown)
    for link in links:
        if os.path.exists(os.path.join(src,link[2:-2]+".md")):
            rawmarkdown = rawmarkdown.replace(link, "<a href=\"/wiki/"+link[2:-2]+".html\">"+link[2:-2].split("/")[-1]+"</a>")
        elif os.path.exists(os.path.join(src,link[2:-2]+"/index.md")):
            rawmarkdown = rawmarkdown.replace(link, "<a href=\"/wiki/"+link[2:-2]+"\">"+link[2:-2].split("/")[-1]+"</a>")
        else:
            foundpath = FindFile(link[2:-2]+".md").replace(".md","").replace("\\","/")
            rawmarkdown = rawmarkdown.replace(link, "<a href=\"/wiki/"+foundpath+".html\">"+foundpath.split("/")[-1]+"</a>")
    embeds = re.findall(r'\{\{[^\{\}]+?\}\}', rawmarkdown,re.MULTILINE)
    for embed in embeds:
        path_and_args = embed[2:-2].split("|")
        path = path_and_args[0]
        if os.path.exists(os.path.join(src,path+".embed.md")):
            path = src+path+".embed.md"
        else:
            foundpath = FindFile(path+".embed.md").replace("\\","/")
            path = src+foundpath
        with open(path,"r") as f:
            embedcontent = f.read().replace("\r\n","\n").replace("\\}","}")
        if len(path_and_args) > 1:
            i = 1
            for arg in path_and_args[1:]:
                embedcontent = embedcontent.replace("$"+str(i)+"$", arg)
                i+=1
        rawmarkdown = rawmarkdown.replace(embed, ConvertStrToHtml(embedcontent))
    links = re.findall(r'\[[^\[^\]]+\]\[[^\[^\]]+\]',rawmarkdown)
    for link in links:
        name = link[1:].split("]",1)[0]
        href = link[1:].split("[",1)[1].split("]",1)[0]
        if(href.startswith("http://") or href.startswith("https://")):
            rawmarkdown = rawmarkdown.replace(link, "<a href=\""+href+"\">"+name+"</a>")
        elif os.path.exists(os.path.join(src,href+".md")):
            rawmarkdown = rawmarkdown.replace(link, "<a href=\"/wiki/"+href+".html\">"+name+"</a>")
        else:
            foundpath = FindFile(href+".md").replace(".md","").replace("\\","/")
            rawmarkdown = rawmarkdown.replace(link, "<a href=\"/wiki/"+foundpath+".html\">"+name+"</a>")
    converted = mark.convert(rawmarkdown)
    return converted

def ConvertToHtml(fpath):
    with open(fpath,"r") as f:
        rawmarkdown = f.read().replace("\r\n","\n")
        return ConvertStrToHtml(rawmarkdown)
        

template = template.replace("@DOCUMENTLIST",str(documentlist)).replace("@NAMELIST",str(namelist))

for root, subdirs, files in os.walk(src):
    if(not os.path.exists(dst+root[len(src):])):
        os.mkdir(dst+root[lensrc:])
    for file in files:
        if file.endswith(".embed.md"):
            continue
        fpath = os.path.join(root, file)
        filetree = ""
        IterateFileTree(filetreedict,"/"+os.path.join(root[lensrc:], file).replace("\\","/"), True)
        with open(dst+fpath[len(src):].replace(".md",".html"), "w") as r:
            converted = ConvertToHtml(fpath)
            r.write(template.replace("@CONTENT",converted).replace("@FILETREE",filetree))