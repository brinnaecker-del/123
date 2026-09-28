import sys; sys.path.insert(0,'/home/user/123/pledge-cash/scripts')
import pandas as pd, numpy as np, pyfixest as pf
import mechanism as M
S='/tmp/claude-0/-home-user-123/20da8b1d-5dd1-59d1-a1e8-2b17264f4263/scratchpad'
raw=f'{S}/raw'
panel=pd.read_csv(f'{S}/real/panel.csv',dtype={'stkcd':str})
print('panel N',len(panel),panel.stkcd.nunique())
panel['ipo_age']=(panel['year']-panel['listyear']).clip(0,40).astype(int)
mret=M.monthly_index(raw); pr=M.pressure(raw,mret)
d=panel.merge(pr,on=['stkcd','year'],how='left'); d['Pressure']=d['Pressure'].fillna(0)
X=' + '.join(M.CONTROLS)
base=d.dropna(subset=['Cash','Pledge']+M.CONTROLS)
def est(f,data,k):
    r=pf.feols(f,data=data,vcov={'CRV1':'stkcd'}); t=r.tidy().loc[k]
    return f"{t['Estimate']:+.4f} (p={t['Pr(>|t|)']:.3f}, N={r._N})"
for lab,sub in [('全样本',base),('上市满3年',base[base.ipo_age>=3]),('上市满5年',base[base.ipo_age>=5])]:
    pl=sub[sub.Pledge>0]
    print(lab)
    print('  基准 Pledge           ',est(f'Cash ~ Pledge + {X} | stkcd + year',sub,'Pledge'))
    print('  Pressure(全)          ',est(f'Cash ~ Pledge + Pressure + {X} | stkcd + year + ipo_age',sub,'Pressure'))
    print('  Pressure(质押子样本)  ',est(f'Cash ~ Pledge + Pressure + {X} | stkcd + year + ipo_age',pl,'Pressure'))
    sub=sub.assign(Pledge2=sub.Pledge**2)
    r=pf.feols(f'Cash ~ Pledge + Pledge2 + {X} | stkcd + year',data=sub,vcov={'CRV1':'stkcd'})
    b=r.coef(); V=r._vcov; names=list(r._coefnames); i,j=names.index('Pledge'),names.index('Pledge2')
    s1=b['Pledge']+2*b['Pledge2']*1; se1=np.sqrt(V[i,i]+4*V[j,j]+4*V[i,j])
    print(f"  U型FE: 一次{b['Pledge']:+.4f} 平方{b['Pledge2']:+.4f} 右端斜率t={s1/se1:.2f}")
