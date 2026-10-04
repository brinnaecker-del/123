// 将 稿件.md 生成投稿 Word，版式与已录用范文一致：
//   标题 黑体三号加粗居中；作者行 宋体小四居中；正文 宋体小四、1.5 倍行距、首行缩进 2 字符；
//   【摘要】【关键词】【作者信息】标签与一级标题 黑体小四加粗；页边距四周 2.54 cm。
// 用法：node build-docx.js [作者信息.json] [输出路径]
//   作者信息.json 形如 {"byline": "张三  李四", "info": ["作者：李四，……", "张三，……"]}，
//   用于替换稿件中的作者占位符。联系方式不入库，该文件请放在仓库之外。
const { Document, Packer, Paragraph, TextRun, AlignmentType } = require('docx');
const fs = require('fs');
const path = require('path');

const [authorsFile, outArg] = process.argv.slice(2);
const SRC = path.join(__dirname, '稿件.md');
const OUT = outArg || path.join(__dirname, '稿件.docx');
const authors = authorsFile ? JSON.parse(fs.readFileSync(authorsFile, 'utf8')) : null;

const HEI = { ascii: '黑体', eastAsia: '黑体', hAnsi: '黑体', cs: '黑体' };
const SONG = { ascii: '宋体', eastAsia: '宋体', hAnsi: '宋体', cs: '宋体' };
const LINE = { line: 360 };

const song = (text) => new TextRun({ text, font: SONG, size: 24 });
const hei = (text, size = 24) => new TextRun({ text, font: HEI, size, bold: true });

// 「【标签】正文」拆成黑体标签 + 宋体正文
const labelled = (s) => {
  const m = s.match(/^(【[^】]+】)(.*)$/);
  return m ? [hei(m[1]), song(m[2])] : [song(s)];
};

const lines = fs.readFileSync(SRC, 'utf8').split('\n').filter(l => l.trim());
const paras = [];
let section = 0, inInfo = false, infoIdx = 0;

for (const line of lines) {
  if (line.startsWith('# ')) {
    paras.push(new Paragraph({ children: [hei(line.slice(2), 32)],
      alignment: AlignmentType.CENTER, spacing: { ...LINE, after: 120 } }));
  } else if (line.startsWith('> ')) {
    const byline = authors ? authors.byline : line.slice(2);
    paras.push(new Paragraph({ children: [song('  ' + byline)],
      alignment: AlignmentType.CENTER, spacing: { ...LINE, after: 200 } }));
  } else if (line.startsWith('【关键词】')) {
    paras.push(new Paragraph({ children: labelled(line), indent: { firstLine: 480 }, spacing: LINE }));
    paras.push(new Paragraph({ children: [], spacing: { ...LINE, after: 80 } }));
  } else if (line.startsWith('## ')) {
    section++;
    paras.push(new Paragraph({ children: [hei(line.slice(3))],
      indent: { firstLine: 480 }, spacing: { ...LINE, before: 160, after: 60 } }));
  } else if (line.startsWith('【作者信息】')) {
    inInfo = true;
    paras.push(new Paragraph({ children: [], indent: { firstLine: 480 }, spacing: { ...LINE, before: 160, after: 60 } }));
    const text = authors ? '【作者信息】' + authors.info[infoIdx] : line;
    infoIdx++;
    paras.push(new Paragraph({ children: labelled(text), indent: { firstLine: 480 }, spacing: LINE }));
  } else if (inInfo) {
    const text = authors ? authors.info[infoIdx] : line;
    infoIdx++;
    paras.push(new Paragraph({ children: [song(text)], spacing: LINE }));
  } else {
    // 范文第三部分（对策）各段与结尾段段前 8 磅、段后 3 磅
    const spacing = section >= 3 ? { ...LINE, before: 160, after: 60 } : LINE;
    paras.push(new Paragraph({ children: labelled(line), indent: { firstLine: 480 }, spacing }));
  }
}

const doc = new Document({ sections: [{
  properties: { page: { size: { width: 11906, height: 16838 },
    margin: { top: 1440, right: 1440, bottom: 1440, left: 1440, header: 708, footer: 708 } } },
  children: paras,
}] });
Packer.toBuffer(doc).then(b => { fs.writeFileSync(OUT, b); console.log('written', OUT); });
