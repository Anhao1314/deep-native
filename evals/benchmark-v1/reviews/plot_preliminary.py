#!/usr/bin/env python3
"""Plot the retained stage JSON; no model calls. Requires matplotlib==3.9.4."""
import argparse
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--input',required=True,type=Path)
parser.add_argument('--output',required=True,type=Path,help='Output basename without suffix')
args=parser.parse_args();data=json.loads(args.input.read_text())
matched=data['matched_subset'];groups=[matched['A'],matched['B']]
fig,ax=plt.subplots(figsize=(7.5,4.8))
fig.subplots_adjust(left=.12,right=.96,top=.79,bottom=.22)
bars=ax.bar([0,1],[g['success_rate'] for g in groups],width=.55,
            color=['#687c90','#167c77'],zorder=3)
ax.set_ylim(0,1);ax.set_xlim(-.6,1.6);ax.set_yticks([0,.2,.4,.6,.8,1])
ax.yaxis.set_major_formatter(PercentFormatter(1));ax.set_ylabel('Independent task success')
ax.set_xticks([0,1],['Raw DeepSeek','DeepSeek + Deep Native'])
ax.grid(axis='y',color='#e7ebee',zorder=0)
for name in ['top','right','left']:ax.spines[name].set_visible(False)
ax.spines['bottom'].set_color('#c5cdd3');ax.tick_params(axis='both',length=0,pad=8)
for bar,g in zip(bars,groups):
    ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+.035,
            f"{g['passes']}/{g['runs']} ({100*g['success_rate']:.0f}%)",
            ha='center',va='bottom',fontsize=12,fontweight='bold')
fig.text(.12,.94,'Preliminary Pilot: matched task pairs',fontsize=16,fontweight='bold')
fig.text(.12,.88,f"{matched['complete_pairs']} tasks, one repetition per arm; all {data['actual_runs']} retained runs remain available.",fontsize=10,color='#52616b')
fig.text(.12,.09,f"B quality wins {matched['B_wins']} / losses {matched['B_losses']} / ties {matched['ties']}. One unpaired B PASS is excluded from this plot.",fontsize=9,color='#52616b')
fig.text(.12,.045,'Descriptive snapshot. No formal statistical conclusion; sandbox limitations apply.',fontsize=9,color='#52616b')
args.output.parent.mkdir(parents=True,exist_ok=True)
fig.savefig(args.output.with_suffix('.png'),dpi=180,facecolor='white')
fig.savefig(args.output.with_suffix('.svg'),facecolor='white',metadata={'Date':None})
args.output.with_suffix('.source.json').write_text(json.dumps({'source':str(args.input),
    'source_sha256':hashlib.sha256(args.input.read_bytes()).hexdigest(),
    'cohort':'matched_subset','A':groups[0]['passes'],'A_n':groups[0]['runs'],
    'B':groups[1]['passes'],'B_n':groups[1]['runs'],'matplotlib':matplotlib.__version__},indent=2)+'\n')
print(args.output.with_suffix('.png'))
