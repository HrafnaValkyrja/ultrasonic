import sys; sys.path.insert(0,'tools')
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'figure.facecolor':'#0d1117','axes.facecolor':'#0d1117','savefig.facecolor':'#0d1117','text.color':'#e6edf3','axes.labelcolor':'#e6edf3','xtick.color':'#e6edf3','ytick.color':'#e6edf3','axes.edgecolor':'#555'})
f,(a,b)=plt.subplots(1,2,figsize=(11,3.8))
# side view along temple: pod extent in x vs vision line
for i,(n,x0,x1,c) in enumerate([('K4',17.65,67.5,'#f0883e'),('K1-thin',33.7,67.5,'#58a6ff')]):
    a.barh(i,x1-x0,left=x0,color=c,height=.5); a.text(x0+1,i,f'{n} L {x1-x0:.2f}',va='center',color='k',fontsize=9)
a.axvline(29.5,color='#f85149',ls='--'); a.text(29.7,1.45,'VISION_X 29.5 (estimate)',color='#f85149',fontsize=8)
a.set_yticks([]); a.set_xlabel('pod x along temple (mm)'); a.set_title('Vision line: K4 front 11.85 mm inside; k1t clear 4.2')
# clearances
n=['floor nom','floor RSS','floor worst','lid worst']; v=[0.65,0.44,0.163,0.112]
b.bar(n,v,color=['#3fb950','#3fb950','#d29922','#d29922']); b.set_ylabel('clearance mm'); b.set_title('K4 stack clearances (k4_heights)')
for i,x in enumerate(v): b.text(i,x+.01,f'{x}',ha='center',fontsize=9)
plt.tight_layout(); plt.savefig('docs/proof/physical/physical.png',dpi=130)
