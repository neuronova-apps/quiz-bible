#!/usr/bin/env python3
"""Phase 1 static quality checks for Neuronova Apps."""
from __future__ import annotations
import os,re,sys,xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote,urlparse
ROOT=Path(__file__).resolve().parents[1]
REQUIRED_FILES=("index.html","favicon.svg","privacy/index.html","sitemap.xml","README.md",".nojekyll")
SKIP_DIRS={".git","node_modules","build","dist",".gradle",".idea",".kotlin"}
TEXT_SUFFIXES={".html",".css",".js",".json",".md",".xml",".yml",".yaml",".py",".txt",".svg"}
CONFLICT_RE=re.compile(r"(?m)^(<<<<<<< |>>>>>>> )"); CSS_URL_RE=re.compile(r"url\(\s*([^)]+?)\s*\)",re.I)
ERRORS=[]; HTML_CACHE={}
def error(m): ERRORS.append(m)
def iter_repo_files():
    for p in ROOT.rglob("*"):
        if p.is_file() and not any(x in SKIP_DIRS for x in p.relative_to(ROOT).parts): yield p
def read_text(p): return p.read_text(encoding="utf-8",errors="strict")
class HTMLInfo(HTMLParser):
    def __init__(self,source):
        super().__init__(convert_charrefs=True); self.source=source; self.ids=set(); self.duplicate_ids=set(); self.refs=[]; self.meta_name={}; self.meta_property={}; self.canonical=None; self.icons=[]; self.tags={}; self._in_title=False; self._title=[]
    @property
    def title(self): return " ".join("".join(self._title).split())
    def handle_starttag(self,tag,attrs):
        tag=tag.lower(); self.tags[tag]=self.tags.get(tag,0)+1; d={k.lower():v or "" for k,v in attrs}; i=d.get("id")
        if i:
            if i in self.ids:self.duplicate_ids.add(i)
            self.ids.add(i)
        if tag=="title":self._in_title=True
        if tag=="meta":
            c=d.get("content","").strip(); n=d.get("name","").strip().lower(); p=d.get("property","").strip().lower()
            if n:self.meta_name[n]=c
            if p:self.meta_property[p]=c
        if tag=="link":
            h=d.get("href","").strip(); rel={x.lower() for x in d.get("rel","").split()}
            if h:
                self.refs.append(("href",h))
                if "canonical" in rel:self.canonical=h
                if "icon" in rel or "shortcut" in rel:self.icons.append(h)
        a={"a":"href","script":"src","img":"src","source":"src","iframe":"src","audio":"src","video":"src"}.get(tag)
        if a and d.get(a):self.refs.append((a,d[a].strip()))
        if tag=="video" and d.get("poster"):self.refs.append(("poster",d["poster"].strip()))
        if d.get("srcset"):
            for c in d["srcset"].split(","):
                v=c.strip().split()[0] if c.strip() else ""
                if v:self.refs.append(("srcset",v))
    def handle_endtag(self,tag):
        if tag.lower()=="title":self._in_title=False
    def handle_data(self,data):
        if self._in_title:self._title.append(data)
def parse_html(path):
    path=path.resolve()
    if path in HTML_CACHE:return HTML_CACHE[path]
    p=HTMLInfo(path)
    try:p.feed(read_text(path));p.close()
    except Exception as e:error(f"HTML parse error in {path.relative_to(ROOT)}: {e}")
    HTML_CACHE[path]=p;return p
def pages_context():
    r=os.getenv("GITHUB_REPOSITORY","").strip()
    if "/" not in r:return None,None
    o,n=r.split("/",1);return f"{o}.github.io",f"/{n}/"
PAGES_HOST,PAGES_PREFIX=pages_context()
def local_target(source,reference):
    value=reference.strip().strip("\"'"); parsed=urlparse(value)
    if not value or value.startswith("#"):return source,unquote(parsed.fragment)
    if parsed.scheme in {"mailto","tel","data","javascript"}:return None,""
    if parsed.scheme in {"http","https"} or parsed.netloc:
        if not(PAGES_HOST and PAGES_PREFIX and parsed.netloc==PAGES_HOST and parsed.path.startswith(PAGES_PREFIX)):return None,""
        target=ROOT/unquote(parsed.path[len(PAGES_PREFIX):])
    else:
        part=unquote(parsed.path)
        if not part:target=source
        elif part.startswith("/"):return None,""
        else:target=source.parent/part
    try:resolved=target.resolve();resolved.relative_to(ROOT)
    except ValueError:error(f"Reference escapes repository: {source.relative_to(ROOT)} -> {reference}");return None,""
    if resolved.is_dir() or reference.split("?",1)[0].split("#",1)[0].endswith("/"):resolved=resolved/"index.html"
    return resolved,unquote(parsed.fragment)
def check_reference(source,attribute,reference):
    target,frag=local_target(source,reference)
    if target is None:return
    if not target.exists() or not target.is_file():error(f"Broken local {attribute} in {source.relative_to(ROOT)}: {reference}");return
    if frag and target.suffix.lower() in {".html",".htm"} and frag not in parse_html(target).ids:error(f"Missing fragment #{frag} referenced from {source.relative_to(ROOT)} to {target.relative_to(ROOT)}")
def check_required_structure():
    for r in REQUIRED_FILES:
        if not(ROOT/r).exists():error(f"Missing required file: {r}")
def check_conflict_markers():
    for p in iter_repo_files():
        if p.suffix.lower() not in TEXT_SUFFIXES and p.name!=".nojekyll":continue
        try:t=read_text(p)
        except UnicodeDecodeError:continue
        if CONFLICT_RE.search(t):error(f"Merge-conflict marker found in {p.relative_to(ROOT)}")
def check_html_files():
    for p in iter_repo_files():
        if p.suffix.lower() not in {".html",".htm"}:continue
        i=parse_html(p);r=p.relative_to(ROOT)
        for tag in ("html","head","body"):
            if not i.tags.get(tag):error(f"Missing <{tag}> in {r}")
        if not i.title:error(f"Missing or empty <title> in {r}")
        for d in sorted(i.duplicate_ids):error(f"Duplicate id '{d}' in {r}")
        for a,ref in i.refs:check_reference(p,a,ref)
def check_css_resources():
    for p in iter_repo_files():
        if p.suffix.lower()!=".css":continue
        try:t=read_text(p)
        except UnicodeDecodeError:continue
        for m in CSS_URL_RE.finditer(t):
            v=m.group(1).strip().strip("\"'")
            if v and not v.startswith(("#","data:","var(")):check_reference(p,"CSS url()",v)
def require_meta(i,kind,key,label):
    m=i.meta_name if kind=="name" else i.meta_property
    if not m.get(key):error(f"Missing SEO metadata {label} in {i.source.relative_to(ROOT)}")
def check_seo():
    p=ROOT/"index.html"; i=parse_html(p);require_meta(i,"name","description","meta description")
    for k in ("og:site_name","og:title","og:description","og:url","og:image"):require_meta(i,"property",k,k)
    for k in ("twitter:card","twitter:title","twitter:description","twitter:image"):require_meta(i,"name",k,k)
    if not i.canonical:error("Homepage is missing rel=canonical")
    if not i.icons:error("Homepage is missing a favicon link")
    if PAGES_HOST and PAGES_PREFIX and i.canonical:
        e=f"https://{PAGES_HOST}{PAGES_PREFIX}"
        if i.canonical!=e:error(f"Homepage canonical mismatch: expected {e}, found {i.canonical}")
        if i.meta_property.get("og:url")!=e:error(f"og:url mismatch: expected {e}, found {i.meta_property.get('og:url','')}")
    for k,m in (("og:image",i.meta_property),("twitter:image",i.meta_name)):
        if m.get(k):check_reference(p,k,m[k])
    q=ROOT/"privacy/index.html"
    if q.exists():
        x=parse_html(q);require_meta(x,"name","description","privacy meta description")
        if not x.canonical:error("privacy/index.html is missing rel=canonical")
def check_sitemap():
    p=ROOT/"sitemap.xml"
    try:tree=ET.parse(p)
    except ET.ParseError as e:error(f"Invalid sitemap.xml: {e}");return
    loc=[(e.text or "").strip() for e in tree.iter() if e.tag.rsplit("}",1)[-1]=="loc"];loc=[x for x in loc if x]
    if not loc:error("sitemap.xml contains no <loc> entries");return
    if len(loc)!=len(set(loc)):error("sitemap.xml contains duplicate <loc> entries")
    for x in loc:
        if not x.startswith("https://"):error(f"Sitemap URL must use https: {x}")
    i=parse_html(ROOT/"index.html")
    if i.canonical and i.canonical not in loc:error(f"Homepage canonical missing from sitemap.xml: {i.canonical}")
    q=ROOT/"privacy/index.html"
    if q.exists():
        x=parse_html(q)
        if x.canonical and x.canonical not in loc:error(f"Privacy canonical missing from sitemap.xml: {x.canonical}")
def main():
    check_required_structure();check_conflict_markers();check_html_files();check_css_resources();check_seo();check_sitemap()
    if ERRORS:
        print(f"\nQuality checks failed with {len(ERRORS)} issue(s):")
        for e in ERRORS:print(f"  - {e}")
        return 1
    n=sum(1 for p in iter_repo_files() if p.suffix.lower() in {".html",".htm"});print(f"Quality checks passed: {n} HTML file(s), local links/resources, SEO and sitemap are consistent.");return 0
if __name__=="__main__":sys.exit(main())
