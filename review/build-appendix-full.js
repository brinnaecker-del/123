const {Document,Packer,Paragraph,TextRun,AlignmentType,Table,TableRow,TableCell,
       WidthType,ShadingType,PageOrientation} = require('docx');
const fs=require('fs');
const A=JSON.parse(fs.readFileSync('/tmp/claude-0/appendix.json','utf8'));
const AU=JSON.parse(fs.readFileSync('/tmp/claude-0/author_a34.json','utf8'));
const A4D=JSON.parse(fs.readFileSync('/tmp/claude-0/a4.json','utf8'));
const YS=A.YS;
const F ={ascii:'Times New Roman',eastAsia:'宋体',hAnsi:'Times New Roman'};
const FH={ascii:'Arial',eastAsia:'黑体',hAnsi:'Arial'};
const W=14678, HDRF='DCE6F1';
const T=(t,o={})=>new TextRun({text:String(t),font:o.h?FH:F,size:o.size||18,
  bold:!!o.b,color:o.color||'000000'});
const P=(runs,o={})=>new Paragraph({children:Array.isArray(runs)?runs:[T(runs,o)],
  spacing:{line:o.line||260,before:o.before||0,after:o.after==null?60:o.after},alignment:o.align});
const Cap=(t)=>new Paragraph({children:[T(t,{h:true,b:true,size:21})],
  spacing:{before:300,after:120},alignment:AlignmentType.CENTER,keepNext:true});
const Note=(t)=>new Paragraph({children:[T(t,{size:16,color:'404040'})],
  spacing:{before:60,after:200}});
function TBL(head,rows,widths,opts={}){
  const tot=widths.reduce((a,b)=>a+b,0), cols=widths.map(w=>Math.round(w/tot*W));
  const cell=(v,i,hd)=>new TableCell({width:{size:cols[i],type:WidthType.DXA},
    shading:hd?{type:ShadingType.CLEAR,fill:HDRF,color:'auto'}:undefined,
    margins:{top:40,bottom:40,left:70,right:70},verticalAlign:'center',
    children:[new Paragraph({children:[T(v,{size:16,b:hd})],spacing:{line:220,before:0,after:0},
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

// A1 —— 按正文表6 口径重算
push(Cap('附表A1　13项指标留一法（LOO）稳健性检验完整结果'));
push(TBL(['剔除指标','所属子系统','DMPI(2016)','DMPI(2025)','发展最弱年数（共10年）'],
  A.A1.map(r=>[r.code+' '+r.name.replace(/（.*/,''),r.sub,r.d2016.toFixed(3),r.d2025.toFixed(3),String(r.cnt)]),
  [4200,1600,1700,1700,2200],{numFrom:1}));
const cnts=A.A1.map(r=>r.cnt), ge3=cnts.filter(x=>x>=3).length;
push(Note('注：逐一剔除13项指标中的一项后，子系统内部对其余指标仍按等权重新计算US、UD、UE，再按式（4）重算MPI协调指数。'
 +`13项设定中有${ge3}项发展最弱年数不少于3年，仅剔除S4、D3两项设定下降至2年，年数区间为${Math.min(...cnts)}—${Math.max(...cnts)}年。`
 +'本表S1、S4、D3、E2、E4五项与正文表6所列节选值逐项一致。'
 +'数据来源：历年《西藏自治区国民经济和社会发展统计公报》、财政决算资料、人力资源和社会保障统计资料、生态环境状况公报及林草公报。'));

// A2
push(Cap('附表A2　2016—2025年人均化与相对全国水平处理所用辅助基础序列'));
push(TBL(['年份','西藏自治区年末常住人口（万人）','全国城镇居民人均可支配收入（元）','全国农村居民人均可支配收入（元）','全国城乡居民收入比'],
  YS.map((y,i)=>[String(y),A.AUX.pop[i].toFixed(2),A.AUX.nu[i].toLocaleString('en-US'),
                 A.AUX.nr[i].toLocaleString('en-US'),A.AUX.ratio[i].toFixed(2)]),
  [1400,3400,3400,3400,2400],{numFrom:1}));
push(Note('注：西藏自治区年末常住人口取自历年《西藏自治区国民经济和社会发展统计公报》，其中2020年为第七次全国人口普查数；'
 +'全国城镇、农村居民人均可支配收入取自国家统计局历年发布的《居民收入和消费支出情况》。'
 +'城乡居民收入比＝城镇居民人均可支配收入／农村居民人均可支配收入，样本期内逐年下降，反映全国城乡收入差距持续收窄。'
 +'该三条序列用于S1（人均化）、S2（与全国差距）、D2（相对全国水平）、D4（人均化）四项指标的换算。'));

// A3 —— 列头改为「占七地市合计比重」
push(Cap('附表A3　2024年西藏七地市经济规模、财政自给率与文旅发展'));
const a3h=AU.A3[0].slice(); a3h[2]='占七地市合计比重（%）';
push(TBL(a3h, AU.A3.slice(1), [1300,1500,1900,2100,1500,1500,2000,2000,1600],{numFrom:1}));
push(Note('注：财政自给率＝一般公共预算收入／一般公共预算支出。除拉萨市外，其余六个地市（地区）财政自给率均低于11%。'
 +'表末合计行为七地市（地区）加总值，与2024年全区统计公报所载地区生产总值（2764.94亿元）及正文D3分母所用的'
 +'含第五次全国经济普查修订口径（2789.07亿元）均不相同，比重列的分母为七地市合计。'
 +'数据来源：西藏自治区及七地市2024年国民经济和社会发展统计公报、财政决算资料。各分项占比之和与100%的微小误差为四舍五入所致。'));

// A4 —— 按面板数据重算
push(Cap('附表A4　2016—2024年74个区县层面经济规模空间分异'));
push(TBL(['年份','总量口径泰尔指数（74区县）','剔除城关区后泰尔指数（73区县）','总量—人均秩相关系数（户籍口径）'],
  A4D.map(r=>[String(r.y),r.t74.toFixed(3),r.t73.toFixed(3),r.sp.toFixed(3)]),
  [1600,4400,4400,4300],{numFrom:1}));
push(Note('注：泰尔指数采用份额熵形式 T=Σ(GDP_i/GDP)×ln[(GDP_i/GDP)×n]（n为区县数）。'
 +'总量口径泰尔指数于2019年达到峰值0.770，2024年降至0.621；剔除城关区后的73区县泰尔指数由2016年0.362升至2024年0.412，'
 +'表明总量口径差距的收窄主要由城关区份额下降所驱动。'
 +'秩相关系数为各区县地区生产总值排名与人均地区生产总值（以户籍人口为基数）排名的斯皮尔曼秩相关系数，'
 +'由2016年的0.344降至2024年的0.178，与正文§5(四)所引一致，反映经济总量分布与人均分布的一致性趋于减弱。'
 +'2024年城关区按户籍口径人均地区生产总值在74个区县中排名第5位，常住口径下排名第14位。'
 +'数据来源：74个区县2016—2024年统计资料及历年国民经济和社会发展统计公报。'));

const doc=new Document({creator:'附录',title:'附录',
  styles:{default:{document:{run:{font:F,size:18},paragraph:{spacing:{line:260}}}}},
  sections:[{properties:{page:{size:{orientation:PageOrientation.LANDSCAPE},
    margin:{top:1080,bottom:1080,left:1080,right:1080}}},children:c}]});
Packer.toBuffer(doc).then(b=>{fs.writeFileSync('/home/user/123/review/F8-附录.docx',b);
  console.log('written',b.length,'bytes;',c.length,'blocks');});
