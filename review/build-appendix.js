const {Document,Packer,Paragraph,TextRun,AlignmentType,Table,TableRow,TableCell,
       WidthType,ShadingType,BorderStyle,PageOrientation,HeadingLevel} = require('docx');
const fs=require('fs');
const A=JSON.parse(fs.readFileSync('/tmp/claude-0/appendix.json','utf8'));
const YS=A.YS;

const F ={ascii:'Times New Roman',eastAsia:'宋体',hAnsi:'Times New Roman'};
const FH={ascii:'Arial',eastAsia:'黑体',hAnsi:'Arial'};
const W=14678, HDRF='DCE6F1';

const T=(t,o={})=>new TextRun({text:String(t),font:o.h?FH:F,size:o.size||18,
  bold:!!o.b,italics:!!o.i,color:o.color||'000000'});
const P=(runs,o={})=>new Paragraph({children:Array.isArray(runs)?runs:[T(runs,o)],
  spacing:{line:o.line||260,before:o.before||0,after:o.after==null?60:o.after},
  alignment:o.align,indent:o.indent});
const Cap=(t)=>new Paragraph({children:[T(t,{h:true,b:true,size:21})],
  spacing:{before:300,after:120},alignment:AlignmentType.CENTER,keepNext:true});
const Note=(t)=>new Paragraph({children:[T(t,{size:16,color:'404040'})],
  spacing:{before:60,after:200},alignment:AlignmentType.LEFT});

function TBL(head,rows,widths,opts={}){
  const tot=widths.reduce((a,b)=>a+b,0), cols=widths.map(w=>Math.round(w/tot*W));
  const cell=(v,i,hd)=>new TableCell({
    width:{size:cols[i],type:WidthType.DXA},
    shading:hd?{type:ShadingType.CLEAR,fill:HDRF,color:'auto'}:
      (opts.shadeRows&&opts.shadeRows(v,i)?{type:ShadingType.CLEAR,fill:'FFF7E6',color:'auto'}:undefined),
    margins:{top:40,bottom:40,left:70,right:70},
    verticalAlign:'center',
    children:[new Paragraph({children:[T(v,{size:16,b:hd})],
      spacing:{line:220,before:0,after:0},
      alignment:(hd||i>=(opts.numFrom==null?1:opts.numFrom))?AlignmentType.CENTER:AlignmentType.LEFT})]});
  return new Table({columnWidths:cols,width:{size:W,type:WidthType.DXA},
    rows:[new TableRow({tableHeader:true,children:head.map((h,i)=>cell(h,i,true))}),
          ...rows.map(r=>new TableRow({children:r.map((c,i)=>cell(c,i,false))}))]});
}
const c=[]; const push=(...x)=>x.forEach(i=>Array.isArray(i)?c.push(...i):c.push(i));

push(new Paragraph({children:[T('附　　录',{h:true,b:true,size:30})],
  alignment:AlignmentType.CENTER,spacing:{after:80}}));
push(new Paragraph({children:[T('《国家战略功能约束下西藏高质量发展的三元协调评价》',{size:19,color:'595959'})],
  alignment:AlignmentType.CENTER,spacing:{after:320}}));

// ── 附表A1 ──
push(Cap('附表A1　关键指标留一法（LOO）完整结果'));
push(TBL(['剔除指标','所属子系统','DMPI(2016)','DMPI(2025)','发展最弱年数（共10年）'],
  A.A1.map(r=>[r.code+' '+r.name.replace(/（.*/,''),r.sub,r.d2016.toFixed(3),r.d2025.toFixed(3),String(r.cnt)]),
  [4200,1600,1700,1700,2200],{numFrom:1}));
const cnts=A.A1.map(r=>r.cnt), ge3=cnts.filter(x=>x>=3).length;
push(Note('注：逐一剔除单项指标后按其余设定不变重算。“发展最弱年数”指样本期10年中发展子系统指数在三者中最低的年数。'
  +`13项设定下该年数在 ${Math.min(...cnts)}—${Math.max(...cnts)} 年之间，其中 ${ge3} 项设定下不少于3年，'
  + '故“2018—2022年为发展相对滞后的重要阶段”这一方向性判断总体成立，但具体年数不稳健。`));

// ── 附表A2 ──
push(Cap('附表A2　用于人均化与相对化处理的辅助基础序列'));
push(TBL(['序列','单位',...YS.map(String)],
  [['西藏年末常住人口','万人',...A.AUX.pop.map(v=>String(v))],
   ['全国农村居民人均可支配收入','元',...A.AUX.nr.map(v=>String(v))],
   ['全国城镇居民人均可支配收入','元',...A.AUX.nu.map(v=>String(v))],
   ['全国城乡居民收入比','倍',...A.AUX.ratio.map(v=>v.toFixed(4))]],
  [3600,900,...YS.map(()=>1018)],{numFrom:2}));
push(Note('注：西藏年末常住人口据历年《西藏自治区国民经济和社会发展统计公报》，其中2020年为第七次全国人口普查数；'
 +'全国城乡居民人均可支配收入据国家统计局历年《居民收入和消费支出情况》；全国城乡居民收入比由前两项相除得出。'
 +'该三条序列用于：S1（人均化）、S2（与全国差距）、D2（相对全国水平）、D4（人均化）。'));

// ── 附表A3 / A4 占位 ──
push(Cap('附表A3　2024年七地市（区）主要经济指标'));
push(P([T('【待补】',{b:true,color:'C00000'}),
        T('本表对应正文第五部分（四）的地市层面补充观察，需列出2024年拉萨市、日喀则市、昌都市、林芝市、'
        +'山南市、那曲市、阿里地区七地市（区）的地区生产总值、占七地市合计比重、一般公共预算收入与财政自给率。',{size:18})]));
push(Note('注：正文引用值为“拉萨市占七地市合计的35.81%，阿里地区仅3.83%，除拉萨外的六个地市（区）财政自给率均低于11%”，请据此补齐全表。'));

push(Cap('附表A4　2016—2024年74个区县经济规模面板及空间分异检验'));
push(P([T('【待补】',{b:true,color:'C00000'}),
        T('本表对应正文第五部分（四）的县域层面补充观察，需列出74个区县2016—2024年的地区生产总值，'
        +'以及按总量口径与人均口径（户籍、常住两种人口口径）计算的泰尔指数、斯皮尔曼秩相关系数。',{size:18})]));
push(Note('注：正文引用值为“总量口径泰尔指数自2019年峰值0.770降至2024年的0.621；剔除城关区后其余73个县域由2016年的0.362升至2024年的0.412；'
 +'总量与人均排序的斯皮尔曼秩相关由2016年的0.344降至2024年的0.178”，请据此补齐全表。'));

// ── 附表A5 原始值 ──
push(Cap('附表A5　13项指标标准化前取值（2016—2025年）'));
push(TBL(['编码','三级指标','方向',...YS.map(String)],
  A.IND.map(x=>[x.code,x.name,x.dir,...x.raw.map(v=>{
    const a=Math.abs(v); return a>=1000?v.toFixed(0):(a>=100?v.toFixed(1):(a>=10?v.toFixed(2):v.toFixed(3)));})]),
  [600,3400,620,...YS.map(()=>1005)],{numFrom:3}));
push(Note('注：各项取值口径见正文表1。S1、D2、D3、D4为按附表A2辅助序列换算所得；'
 +'D3分母的地区生产总值采用含第五次全国经济普查修订的最新核算口径；'
 +'D5取统计公报“规上工业主要产品产量”所载发电量。'));

// ── 附表A6 标准化后 ──
push(Cap('附表A6　13项指标标准化后取值'));
push(TBL(['编码','三级指标','下限','上限',...YS.map(String)],
  A.IND.map(x=>[x.code,x.name,String(x.lo),String(x.hi),...x.std.map(v=>v.toFixed(4))]),
  [600,3000,700,700,...YS.map(()=>968)],{numFrom:2}));
push(Note('注：按正文式(1)（正向）或式(2)（逆向）以固定基准标准化，超出[0,1]的部分截断，'
 +'再按式(3) x′=0.98x*+0.01 平移压缩至[0.01,0.99]。子系统指数为各子系统内标准化值的等权平均。'));

// ── 附表A7 权重与缺口 ──
push(Cap('附表A7　CRITIC—熵值组合权重与结构性贡献缺口完整结果'));
const codes=A.IND.map(x=>x.code);
push(TBL(['编码','三级指标','熵值权重','CRITIC权重','组合权重','结构性贡献缺口（样本期均值）'],
  A.IND.map(x=>[x.code,x.name,A.WE[x.code].toFixed(4),A.WC[x.code].toFixed(4),
                A.W[x.code].toFixed(4),(A.GAP[x.code]*100).toFixed(2)+'%']),
  [600,4200,1700,1700,1700,3000],{numFrom:2}));
const w4=codes.map(k=>A.W[k]).sort((a,b)=>b-a).slice(0,4).reduce((a,b)=>a+b,0);
push(Note(`注：组合权重由熵值权重与CRITIC权重相乘后归一得出，仅用于结构性贡献缺口诊断与稳健性对照，不参与子系统合成（子系统内为等权）。`
 +`前四项组合权重合计 ${w4.toFixed(4)}，其余九项合计 ${(1-w4).toFixed(4)}；安全类四项权重均低于1.2%。`
 +`结构性贡献缺口为各指标组合权重与其偏离度(1−x′)之积占当年13项该乘积之和的比重，逐年计算后取样本期均值，合计为100%。`));

// ── 附表A8 子系统指数与MPI ──
push(Cap('附表A8　三子系统综合指数与MPI协调指数（与正文表3对照）'));
push(TBL(['年份','安全 US','发展 UD','生态 UE','M 均值','S² 总体方差','MPI协调指数 D'],
  YS.map((y,i)=>{
    const us=A.SUBIDX.US[i],ud=A.SUBIDX.UD[i],ue=A.SUBIDX.UE[i];
    const M=(us+ud+ue)/3, S2=((us-M)**2+(ud-M)**2+(ue-M)**2)/3;
    return [String(y),us.toFixed(4),ud.toFixed(4),ue.toFixed(4),M.toFixed(4),S2.toFixed(6),(M-S2/M).toFixed(4)];}),
  [1200,1800,1800,1800,1800,2200,2400],{numFrom:1}));
push(Note('注：本表为正文表3的四位小数版本，并列出MPI计算的中间量。D = M − S²/M，其中M为三子系统综合指数的算术平均，'
 +'S²为其总体方差。正文表3所载为三位小数的舍入结果。'));

const doc=new Document({creator:'附录',title:'附录',
  styles:{default:{document:{run:{font:F,size:18},paragraph:{spacing:{line:260}}}}},
  sections:[{properties:{page:{size:{orientation:PageOrientation.LANDSCAPE},
    margin:{top:1080,bottom:1080,left:1080,right:1080}}},children:c}]});
Packer.toBuffer(doc).then(b=>{fs.writeFileSync('/home/user/123/review/F8-附录.docx',b);
  console.log('written',b.length,'bytes;',c.length,'blocks');});
