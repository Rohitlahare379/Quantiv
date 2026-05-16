import React from 'react';
import { Trash2 } from 'lucide-react';

interface WorkspaceSidebarProps {
  savedStrategies: any[];
  activeStrategyId: number | null;
  loadStrategy: (s: any) => void;
  deleteStrategy: (id: number) => void;
  STRATEGY_TEMPLATES: any;
  handleTemplateLoad: (id: string) => void;
}

const WorkspaceSidebar: React.FC<WorkspaceSidebarProps> = ({
  savedStrategies, activeStrategyId, loadStrategy, deleteStrategy,
  STRATEGY_TEMPLATES, handleTemplateLoad
}) => {
  return (
    <div className="w-72 border-r border-[#333] bg-[#1e1e1e] flex flex-col overflow-hidden">
      <div className="p-6 border-b border-[#333] flex justify-between items-center">
        <h2 className="text-[14px] font-bold text-white uppercase tracking-widest">Workspace</h2>
        <div className="text-[10px] bg-indigo-500/20 text-indigo-400 px-2 py-0.5 rounded font-bold border border-indigo-500/30">v1.2</div>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
        <div className="mb-6">
          <h3 className="text-[11px] font-bold text-[#555] uppercase tracking-widest mb-3 px-2">Saved Strategies</h3>
          <div className="space-y-1">
             {savedStrategies.map(s => (
               <div 
                 key={s.id}
                 className={`group flex items-center justify-between p-2.5 rounded-lg cursor-pointer transition-none ${
                   activeStrategyId === s.id ? 'bg-[#252526] text-white border border-[#444]' : 'text-[#858585] hover:bg-[#252526] hover:text-[#cccccc] border border-transparent'
                 }`}
                 onClick={() => loadStrategy(s)}
               >
                 <div className="flex flex-col truncate flex-1">
                   <span className="text-[13px] font-medium truncate">{s.name}</span>
                   {s.template_id && STRATEGY_TEMPLATES[s.template_id] && (
                     <span className={`text-[9px] font-bold w-fit mt-0.5 px-1.5 py-0 rounded ${STRATEGY_TEMPLATES[s.template_id].badgeColor}`}>
                       {STRATEGY_TEMPLATES[s.template_id].badge}
                     </span>
                   )}
                 </div>
                 <button 
                   onClick={(e) => { e.stopPropagation(); deleteStrategy(s.id); }}
                   className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-400"
                 >
                   <Trash2 className="w-3.5 h-3.5" />
                 </button>
               </div>
             ))}
             {savedStrategies.length === 0 && <div className="text-[11px] text-[#444] px-2 italic">No saved strategies.</div>}
          </div>
        </div>

        <div>
          <h3 className="text-[11px] font-bold text-[#555] uppercase tracking-widest mb-3 px-2">Templates</h3>
          <div className="space-y-3">
             {Object.entries(STRATEGY_TEMPLATES).map(([id, t]: [string, any]) => (
               <button 
                 key={id} 
                 onClick={() => handleTemplateLoad(id)}
                 className="w-full text-left p-3 rounded-xl bg-[#252526]/30 border border-[#333] hover:border-[#444] transition-none group"
               >
                 <div className="flex items-center justify-between mb-1">
                   <span className="text-[12px] font-bold text-[#cccccc] group-hover:text-white">{t.name}</span>
                   <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${t.badgeColor}`}>{t.badge}</span>
                 </div>
                 <div className="text-[10px] text-[#555]">{t.desc}</div>
               </button>
             ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default WorkspaceSidebar;
