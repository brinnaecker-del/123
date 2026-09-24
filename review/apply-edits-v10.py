# -*- coding: utf-8 -*-
"""v10：按导师意见修订。输入 accepted.xml（已接受导师修订），输出带修订痕迹的 document.xml。"""
import re, sys, html

AUTH = '修订v10'
DATE = '2026-09-24T12:00:00Z'
_id = [9000]
def nid():
    _id[0] += 1
    return str(_id[0])

x = open('accepted.xml', encoding='utf8').read()
PARA_RE = re.compile(r'<w:p[ >].*?</w:p>', re.S)
paras = PARA_RE.findall(x)
new = list(paras)
T = lambda s: ''.join(re.findall(r'<w:t(?: [^>]*)?>([^<]*)</w:t>', s))
esc = lambda s: s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

RUN_RE = re.compile(r'<w:r>(?:(?!</w:r>).)*</w:r>|<w:r [^>]*>(?:(?!</w:r>).)*</w:r>', re.S)
CITE = re.compile(r'(\[\d+(?:[-,]\d+)*\])')

def split_items(p):
    """把段落拆成 [(kind, xml, rPr, text)]；kind='t' 为只含一个 w:t 的文字 run。"""
    head = re.match(r'<w:p[^>]*>(<w:pPr>.*?</w:pPr>)?', p, re.S).group(0)
    body = p[len(head):-len('</w:p>')]
    items, pos = [], 0
    for m in RUN_RE.finditer(body):
        if m.start() > pos:
            items.append(('o', body[pos:m.start()], None, ''))
        r = m.group(0)
        tm = re.fullmatch(r'<w:r>(<w:rPr>.*?</w:rPr>)?<w:t(?: [^>]*)?>([^<]*)</w:t></w:r>', r, re.S)
        if tm:
            items.append(('t', r, tm.group(1) or '', html.unescape(tm.group(2))))
        else:
            items.append(('o', r, None, ''))
        pos = m.end()
    if pos < len(body):
        items.append(('o', body[pos:], None, ''))
    return head, items

def run(rpr, text, deleted=False):
    tag = 'w:delText' if deleted else 'w:t'
    return f'<w:r>{rpr}<{tag} xml:space="preserve">{esc(text)}</{tag}></w:r>'

def sup(rpr):
    if not rpr:
        rpr = '<w:rPr></w:rPr>'
    if 'vertAlign' in rpr:
        return rpr
    return rpr.replace('</w:rPr>', '<w:vertAlign w:val="superscript"/></w:rPr>')

def plain(rpr):
    return re.sub(r'<w:vertAlign [^>]*/>', '', rpr or '')

def ins_runs(rpr, text):
    rpr = plain(rpr)
    out = ''
    for part in CITE.split(text):
        if not part:
            continue
        out += run(sup(rpr) if CITE.fullmatch(part) else rpr, part)
    return f'<w:ins w:id="{nid()}" w:author="{AUTH}" w:date="{DATE}">{out}</w:ins>'

def del_wrap(xml):
    xml = re.sub(r'<w:t( [^>]*)?>', r'<w:delText xml:space="preserve">', xml).replace('</w:t>', '</w:delText>')
    return f'<w:del w:id="{nid()}" w:author="{AUTH}" w:date="{DATE}">{xml}</w:del>'

def replace(i, old, new_text):
    """在第 i 段把 old 改为 new_text；只对差异部分做修订标记。"""
    p = new[i]
    full = T(re.sub(r'<w:del .*?</w:del>', '', p, flags=re.S))
    full = html.unescape(full)
    assert full.count(old) == 1, (i, old, full.count(old))
    # 去掉公共前后缀
    a = 0
    while a < min(len(old), len(new_text)) and old[a] == new_text[a]:
        a += 1
    b = 0
    while b < min(len(old), len(new_text)) - a and old[-1 - b] == new_text[-1 - b]:
        b += 1
    s = full.index(old) + a
    e = full.index(old) + len(old) - b
    ins_text = new_text[a:len(new_text) - b]
    head, items = split_items(p)
    out, off, done, last_rpr = [], 0, False, ''
    for k, (kind, xml, rpr, text) in enumerate(items):
        if kind != 't':
            out.append(xml)
            continue
        L = len(text)
        rs, re_ = off, off + L
        if rs < s or not last_rpr:
            last_rpr = rpr
        if re_ <= s or rs > e or (rs == e and not (s == e and rs == s)):
            # 不重叠；纯插入且插入点位于本 run 起点时在前面插
            if not done and s == e and rs == s and ins_text:
                out.append(ins_runs(rpr, ins_text)); done = True
            out.append(xml); off = re_; continue
        a0, b0 = max(s, rs) - rs, min(e, re_) - rs
        if a0 > 0:
            out.append(run(rpr, text[:a0]))
        if b0 > a0:
            out.append(del_wrap(run(rpr, text[a0:b0])))
        if e <= re_ and not done and ins_text:
            out.append(ins_runs(rpr, ins_text)); done = True
        if b0 < L:
            out.append(run(rpr, text[b0:]))
        off = re_
    if not done and ins_text:
        # 插入点在段末
        out.append(ins_runs(last_rpr, ins_text)); done = True
    new[i] = head + ''.join(out) + '</w:p>'
    chk = html.unescape(T(re.sub(r'<w:del .*?</w:del>', '', new[i], flags=re.S)))
    assert chk == full.replace(old, new_text), (i, chk[:200])

def delete_para(i):
    head, items = split_items(new[i])
    mark = f'<w:del w:id="{nid()}" w:author="{AUTH}" w:date="{DATE}"/>'
    if '<w:rPr>' in head:
        head = re.sub(r'(<w:pPr>.*?<w:rPr>)', r'\1' + mark, head, count=1, flags=re.S)
    else:
        head = head.replace('</w:pPr>', f'<w:rPr>{mark}</w:rPr></w:pPr>')
    body = ''.join(del_wrap(xml) if kind == 't' else xml for kind, xml, rpr, text in items)
    new[i] = head + body + '</w:p>'

BODY_PPR = '<w:pPr><w:ind w:firstLine="420"/><w:jc w:val="both"/><w:rPr>{mark}<w:sz w:val="21"/><w:szCs w:val="21"/></w:rPr></w:pPr>'
BODY_RPR = '<w:rPr><w:sz w:val="21"/><w:szCs w:val="21"/></w:rPr>'
def new_para(text):
    mark = f'<w:ins w:id="{nid()}" w:author="{AUTH}" w:date="{DATE}"/>'
    return '<w:p>' + BODY_PPR.format(mark=mark) + ins_runs(BODY_RPR, text) + '</w:p>'

# ---------------------------------------------------------------- 摘要（批注0、1、7）
replace(4, '将安全界定为由地方财力、城乡收入差距、民生兜底与社会保障覆盖四项制度性条件支撑的独立子系统，与发展、生态并列。',
        '将安全、发展与生态并列为三个独立子系统，分别以4项、5项、4项指标刻画边疆安全屏障的维系条件、高原经济的发展成效与生态安全屏障的守护程度。')
replace(4, '三元协调状态整体改善；', '三元协调状态整体改善，统筹推进稳定、发展、生态、强边的成效在测度上得到体现；')
replace(4, '呈现短板转移的初步迹象；', '呈现短板转移的初步迹象，提示政策资源投向需随短板所在适时调整；')
replace(4, '（3）与同指标集的线性加总指数相比，两者走势高度相关（相关系数为0.979）。三元框架的增量价值不在于改变总体趋势判断，而在于将安全单列为独立子系统后能够识别不同功能之间的阶段性相对短板。',
        '（3）以同一组13项指标按通用的协调、绿色、开放、共享四个维度线性加总作对照，二者走势高度一致（相关系数为0.979），说明三元框架不改变总体趋势判断，'
        '其增量在于按战略功能分组后能够识别不同功能之间的阶段性相对短板，为分阶段确定政策着力点提供依据。'
        '据此提出优化服务业结构、畅通生态价值转化通道、稳固民生保障投入和建立短板动态监测机制等建议。')

# ---------------------------------------------------------------- 引言（批注2）
replace(8, '因此，把安全从背景因素提升为高质量发展评价体系里的独立评价维度，一方面是评价维度与区域功能相匹配的要求，另一方面也契合铸牢中华民族共同体意识、推进各族群众共同富裕的现实需要。如果不把边疆安全、民族团结和民生保障纳入发展质量的评价内核，就容易以单一经济尺度衡量西藏，低估其在国家发展全局中的战略价值。',
        '然而在通用框架中，安全与生态两项屏障功能都未得到与其地位相称的评价，只是缺位的方式不同：安全多被视为发展的背景条件，或被分解并入“社会民生”等指标，缺乏独立的评价维度；'
        '生态虽常以“绿色”维度出现，衡量的却主要是发展方式的资源环境属性，而不是西藏守护国家生态安全屏障这一功能的达成程度。'
        '因此，把安全从背景因素提升为高质量发展评价体系里的独立评价维度，同时把生态由发展的附属属性还原为屏障功能的守护程度，一方面是评价维度与区域功能相匹配的要求，'
        '另一方面也契合筑牢国家生态安全屏障、铸牢中华民族共同体意识、推进各族群众共同富裕的现实需要。'
        '如果不把边疆安全、民族团结、民生保障与生态屏障守护纳入发展质量的评价内核，就容易以单一经济尺度衡量西藏，低估其在国家发展全局中的战略价值。')

replace(11, '把安全从背景性因素提升为独立评价子系统，',
        '把安全从背景性因素提升为独立评价子系统，并以生态屏障功能的守护程度而非发展的“绿色”属性界定生态子系统，')

# ---------------------------------------------------------------- 文献回顾：生态与安全对称
replace(16, '但现有研究对安全功能的处理仍不充分，',
        '生态维度的研究虽较为丰富，但多从生态—经济系统关系、发展与生态安全的冲突等角度展开，较少把生态作为西藏为国家承担的屏障功能、以该功能的守护程度为评价尺度；对安全功能的处理则更不充分，')
replace(19, '容易弱化安全等战略功能的独立地位', '容易弱化安全与生态屏障等战略功能的独立地位')

# ---------------------------------------------------------------- 三元结构的辨析（批注3、4）
replace(22, '它提取的只是回答上述问题所需的核心功能维度。',
        '它提取的只是回答上述问题所需的核心功能维度。这一划分能否成立，还需回答四个追问：它与国土空间规划的“三生”划分有何不同；'
        '为何恰为三类，而不把五大发展理念的若干维度单列；三者为何不能加权求和；它与国外“安全公正空间”研究有何异同。以下依次说明。')
replace(23, '三元划分还需与', '第一，三元结构需与')
replace(23, '相区分[34]。', '相区分[34]。两者都包含“生态”，容易被看作同一分类的改写，但出发点不同：')
replace(23, '“生活”落入安全子系统的民生兜底部分；',
        '“生活”落入安全子系统的民生兜底部分；三生中的“生态”侧重区域内部生态空间的保护与生态产品供给，'
        '三元结构中的生态则指西藏为国家守护的生态安全屏障，以国家规划目标等外部要求为尺度，服务范围超出区域自身；')
replace(23, '三元结构正是针对', '因此，三元结构不能由三生划分替代，它正是针对')
replace(24, '本文不再增设第四类功能，也不合并现有三类。', '第二，三元结构既不增设第四类功能，也不合并现有三类。')
replace(25, '安全与生态也不能并入发展作加权求和，', '第三，安全与生态也不能并入发展作加权求和，')
replace(26, '这一结构与', '第四，这一结构与')

replace(30, '安全要素的兜底作用也最容易被传统框架忽略',
        '安全的兜底作用与生态的边界作用也最容易被传统框架忽略，或被简化为发展的附属指标')

# ---------------------------------------------------------------- 指标说明集中到三（一）（批注5、6）
delete_para(34)
delete_para(35)
replace(46, '指标筛选时剔除了',
        '指标体系按“战略功能—理论构念—统计指标”的逐级映射构建：先由第二部分界定的三类功能确定各子系统所要刻画的内容，'
        '再为每个构念选取具有连续、公开、可比年度序列的统计指标。指标筛选时剔除了')
replace(46, '发展与生态两个子系统沿用既有高质量发展评价与生态评价研究的常见指标口径；安全子系统缺乏现成口径，其构念界定与指标对应已在第二部分单独说明。',
        '三个子系统的构念与指标对应分述如下。')

P_S = ('安全子系统刻画边疆安全屏障功能的维系条件。本文所称“安全”，指稳定与强边所要求的边疆安全屏障功能及其持续维系能力。'
       '边防投入、基层治理、社会治安等更直接的变量缺乏连续、公开、可比的省级年度序列，因此本文转而观测能够反映该功能维系状况的制度性条件，选取四项指标。'
       '地方财力（S1，人均一般公共预算收入）是边疆治理、基层政权运转与公共服务供给的物质基础，财力薄弱则治理投入难以持续。'
       '城乡收入差距（S2，与全国差距的倍数）反映区域内部的社会均衡与共同富裕基础，差距过大容易积累社会矛盾、削弱人心凝聚力。'
       '居民医保财政补助（S3）与养老保险参保率（S4）代表民生兜底的力度与覆盖面，是改善民生、凝聚人心、维系边疆长期稳定的关键环节[35]。'
       '这四项指标与治藏方略“稳定”“强边”的任务内在相关；受统计口径限制，它们是该功能的间接代理而非直接度量。')
P_D = ('发展子系统刻画在安全底线与生态边界之间创造价值的成效，对应治藏方略的“发展”任务与高原经济高质量发展先行区建设要求，从追赶水平与发展动能两个层面选取五项指标。'
       '人均GDP相对全国水平（D1）衡量西藏相对全国的发展追赶程度，取相对值是为了让评价尺度对标国家整体水平；'
       '农村居民人均可支配收入相对全国水平（D2）衡量发展成果向农牧民的传导，农牧区是西藏收入追赶的关键环节。'
       '其余三项对应西藏发展动能的三个主要来源：外向度（D3）衡量依托边境口岸与对外通道的开放发展；'
       '人均接待游客（D4）衡量依托高原生态与民族文化资源的文旅动能；'
       '发电量（D5）衡量以水电、光伏为主体的清洁能源动能，即H2所说“地理势能”向经济动能转化的规模。'
       'D5与清洁能源相关，但衡量的是经济产出规模，因而计入发展子系统而非生态子系统，这一归类对结果的影响见第六部分。')
P_E = ('生态子系统刻画生态安全屏障功能的守护程度。如第二部分所述，生态在三元结构中是发展不可逾越的上界，评价所测的是对这一边界的守护状况，而非生态产出的绝对水平，'
       '因此沿“生态本底—环境质量—开发压力”三个层面选取四项指标。'
       '森林覆盖率（E2）与草原综合植被盖度（E4）刻画高原生态系统的本底状况：草原是西藏面积最大的生态系统，森林集中分布于藏东南，'
       '二者是水源涵养、水土保持与生物多样性维护等屏障服务的主要载体，也是《西藏自治区“十四五”时期生态环境保护规划》设定了明确目标值的指标，'
       '因此以规划目标为标准化上限，使指数直接表达对国家要求的达成程度。'
       '空气质量优良天数比例（E3）刻画环境质量，反映大气环境能否保持优良水平。'
       '单位GDP能耗指数（E1）刻画发展活动对生态边界的资源消耗压力，能耗强度下降意味着以更小的资源环境代价实现同样的发展。'
       '湿地、水源涵养、冰川冻土与生物多样性等更直接反映屏障功能的变量，目前缺乏连续、公开、可比的年度序列，暂未纳入；'
       '与安全子系统相同，现有四项指标是生态屏障功能的主要代理而非完整度量。')
new[46] = new[46] + new_para(P_S) + new_para(P_D) + new_para(P_E)

# ---------------------------------------------------------------- 结论：补政策含义（批注0）
replace(377, '三元协调水平持续改善。',
        '三元协调水平持续改善。这说明统筹推进稳定、发展、生态、强边的总体方向是有效的，三项功能在样本期内同步改善，未出现以一项功能换取另一项功能的情形。')
replace(378, '尚属初步观察。',
        '尚属初步观察。由此，政策资源的配置不宜固定投向某一子系统，而应随当期短板所在适时调整，这是下文第一、三、四条建议的依据。')
replace(379, '说明制约三元协调的因素并非固定不变。',
        '说明制约三元协调的因素并非固定不变。对考核评价而言，这提示对西藏宜把安全屏障与生态屏障功能单列考察，而不宜仅以经济增长或线性加总指数衡量。')

# ---------------------------------------------------------------- 局限：生态代理范围（与安全对称）
replace(390, '三是生态子系统的基准设定对其变动幅度有直接影响：',
        '三是生态子系统的代理范围与基准设定均有局限：湿地、水源涵养、冰川冻土与生物多样性等更直接的屏障功能变量暂未纳入；同时，基准设定对其变动幅度有直接影响：')

# ---------------------------------------------------------------- 英文摘要
replace(437, 'in which security is defined as an independent subsystem supported by four institutional conditions—fiscal capacity, the urban–rural income gap, medical-insurance subsidy and pension coverage—and placed alongside development and ecology.',
        'in which security, development and ecology are treated as three independent subsystems, measured by four, five and four indicators that capture, respectively, '
        'the conditions sustaining the border-security barrier, the performance of the plateau economy and the maintenance of the ecological-security barrier.')
replace(437, 'indicating an overall improvement in triadic coordination;',
        'indicating an overall improvement in triadic coordination and showing that the joint pursuit of stability, development, ecology and border consolidation is reflected in the measurement;')
replace(437, 'is a preliminary sign of a further shift;',
        'is a preliminary sign of a further shift, implying that policy resources should follow the shifting constraint;')
replace(437, '(3) compared with a linear-aggregation index built on the same 13 indicators, the two are highly correlated (r = 0.979). The added value of the triadic framework lies not in revising the overall trend but in making the phase-specific relative constraint identifiable once security is treated as a separate subsystem.',
        '(3) a benchmark index that linearly aggregates the same 13 indicators under conventional dimensions moves closely with the MPI (r = 0.979), so the triadic framework does not change the overall trend; '
        'its added value lies in making the phase-specific relative constraint identifiable once the indicators are grouped by strategic function, which helps set phase-specific policy priorities. '
        'Accordingly, the paper recommends upgrading the service sector, opening channels that turn ecological assets into economic value, sustaining livelihood-security spending and building a dynamic monitoring mechanism for the binding constraint.')

# 拼回
out, k = [], 0
def sub(m):
    global k
    r = new[k]; k += 1
    return r
y = PARA_RE.sub(sub, x)
assert k == len(paras)
open(sys.argv[1], 'w', encoding='utf8').write(y)
print('ok', _id[0] - 9000, 'revision marks')
