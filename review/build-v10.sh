set -e
cd /tmp/claude-0/-home-user-123/4fada015-7f48-5bd0-b693-6003175d3e98/scratchpad
S=/root/.claude/skills/synced/6e457e19-6943-4dd0-aa50-eea02cdd7666_78e1ae23-8672-4d1d-b4f0-04322db522c4/docx/scripts
rm -rf v10t v10c && cp -r up v10t && python3 edit.py v10t/word/document.xml
(cd v10t && rm -f ../v10t.docx && zip -qXr ../v10t.docx .)
cp -r v10t v10c
python3 - <<'PY'
import re,os
d='v10c/word/document.xml'; x=open(d,encoding='utf8').read()
A='w:author="修订v10" w:date="[^"]*"'
x=re.sub(r'<w:(ins|del) w:id="\d+" %s/>'%A,'',x)
x=re.sub(r'<w:del w:id="\d+" %s>.*?</w:del>'%A,'',x,flags=re.S)
x=re.sub(r'<w:ins w:id="\d+" %s>(.*?)</w:ins>'%A,r'\1',x,flags=re.S)
x=re.sub(r'<w:commentRangeStart w:id="\d+"/>|<w:commentRangeEnd w:id="\d+"/>|<w:r><w:commentReference w:id="\d+"/></w:r>','',x)
assert '修订v10' not in x and 'omment' not in x
for pid in ['7C81AE05','15FDE264']:
    x,n=re.subn(r'<w:p w14:paraId="%s">.*?</w:p>'%pid,'',x,flags=re.S); assert n==1
x=x.replace('<w:rPr></w:rPr>','')
open(d,'w',encoding='utf8').write(x)
for f in ['comments.xml','commentsExtended.xml','commentsIds.xml','commentsExtensible.xml','people.xml']:
    p='v10c/word/'+f
    if os.path.exists(p): os.remove(p)
r='v10c/word/_rels/document.xml.rels'; s=open(r,encoding='utf8').read()
s=re.sub(r'<Relationship [^>]*Target="(comments[^"]*|people)\.xml"/>','',s); open(r,'w',encoding='utf8').write(s)
c='v10c/[Content_Types].xml'; s=open(c,encoding='utf8').read()
s=re.sub(r'<Override PartName="/word/(comments[^"]*|people)\.xml"[^>]*/>','',s); open(c,'w',encoding='utf8').write(s)
PY
(cd v10c && rm -f ../v10c.docx && zip -qXr ../v10c.docx .)
python3 $S/office/validate.py v10t.docx --original orig.docx | tail -1
python3 $S/office/validate.py v10c.docx --original orig.docx | tail -1
