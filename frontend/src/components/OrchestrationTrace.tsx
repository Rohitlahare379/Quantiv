import React, { useState } from 'react';
import { Activity, ChevronDown, ChevronRight, Info, Terminal, Timer } from 'lucide-react';

interface TraceEvent {
  agent_id: string;
  event_type: string;
  stage: string;
  timestamp: string;
  duration_ms?: number;
  data: any;
  message: string;
}

interface OrchestrationTraceProps {
  traces: TraceEvent[];
  isOrchestrating: boolean;
}

const OrchestrationTrace: React.FC<OrchestrationTraceProps> = ({ traces, isOrchestrating }) => {
  const [expandedIndices, setExpandedIndices] = useState<number[]>([]);

  const toggleExpand = (index: number) => {
    setExpandedIndices(prev => 
      prev.includes(index) ? prev.filter(i => i !== index) : [...prev, index]
    );
  };

  const totalDuration = traces.length > 0 && traces[traces.length - 1].event_type === 'FINISH'
    ? traces[traces.length - 1].duration_ms || 0
    : 0;

  return (
    <div className="bg-[#1e1e1e] border border-[#333] rounded-xl overflow-hidden mt-10">
      <div className="px-6 py-4 bg-[#252526] border-b border-[#333] flex justify-between items-center">
        <div className="flex items-center space-x-2">
          <Terminal className="w-4 h-4 text-indigo-400" />
          <h3 className="text-[12px] font-bold text-[#858585] uppercase tracking-widest">Orchestration Trace (Causality Engine)</h3>
        </div>
        {totalDuration > 0 && (
          <div className="flex items-center space-x-2 bg-indigo-500/10 px-3 py-1 rounded border border-indigo-500/20">
            <Timer className="w-3 h-3 text-indigo-400" />
            <span className="text-[11px] font-mono text-indigo-400">TOTAL DURATION: {(totalDuration / 1000).toFixed(2)}s</span>
          </div>
        )}
      </div>

      <div className="p-6 space-y-4 max-h-[600px] overflow-y-auto custom-scrollbar font-mono">
        {traces.length === 0 && !isOrchestrating && (
          <div className="text-[#444] italic text-sm py-10 text-center">Awaiting workflow trigger for observability...</div>
        )}
        
        {isOrchestrating && traces.length === 0 && (
          <div className="flex items-center space-x-3 py-10 justify-center">
            <Activity className="w-4 h-4 text-indigo-500 animate-spin" />
            <span className="text-sm text-[#858585]">Capturing execution trace...</span>
          </div>
        )}

        {traces.map((event, i) => (
          <div key={i} className="group border-l-2 border-[#333] hover:border-indigo-500/50 pl-6 py-2 transition-all relative">
            <div className={`absolute left-[-9px] top-4 w-4 h-4 rounded-full border-2 border-[#1e1e1e] ${
              event.event_type === 'START' || event.event_type === 'FINISH' ? 'bg-indigo-500' :
              event.event_type === 'ERROR' ? 'bg-red-500' :
              'bg-[#444] group-hover:bg-indigo-400'
            }`}></div>
            
            <div 
              className="flex items-start justify-between cursor-pointer"
              onClick={() => toggleExpand(i)}
            >
              <div className="flex items-start space-x-4">
                <div className="text-[11px] text-[#555] w-20 pt-1">{event.timestamp.split('T')[1].split('.')[0]}</div>
                <div>
                   <div className="flex items-center space-x-2">
                      <span className={`text-[11px] font-bold uppercase tracking-wider ${
                        event.agent_id === 'Orchestrator' ? 'text-indigo-400' : 'text-[#cccccc]'
                      }`}>{event.agent_id}</span>
                      <span className="text-[10px] text-[#555] opacity-50">/</span>
                      <span className="text-[11px] text-[#858585]">{event.stage}</span>
                   </div>
                   <div className="text-[13px] text-[#cccccc] mt-1">{event.message}</div>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                {event.duration_ms && (
                  <span className="text-[11px] text-indigo-400/60 font-mono">{(event.duration_ms / 1000).toFixed(2)}s</span>
                )}
                {expandedIndices.includes(i) ? <ChevronDown className="w-4 h-4 text-[#555]" /> : <ChevronRight className="w-4 h-4 text-[#555]" />}
              </div>
            </div>

            {expandedIndices.includes(i) && (
              <div className="mt-4 ml-24 bg-[#1a1a1b] rounded border border-[#333] p-4 animate-in fade-in slide-in-from-top-1">
                 <div className="flex items-center space-x-2 mb-3 border-b border-[#333] pb-2">
                    <Info className="w-3 h-3 text-indigo-500" />
                    <span className="text-[10px] font-bold text-[#555] uppercase tracking-widest">Metadata Context</span>
                 </div>
                 <pre className="text-[11px] text-emerald-400/80 leading-relaxed overflow-x-auto whitespace-pre-wrap">
                    {JSON.stringify(event.data || {}, null, 2)}
                 </pre>
                 {Object.keys(event.data || {}).length === 0 && <span className="text-[11px] text-[#444] italic">No extra metadata payload.</span>}
              </div>
            )}
          </div>
        ))}
      </div>
      
      <div className="px-6 py-3 bg-[#1a1a1b] border-t border-[#333] text-[10px] text-[#555] font-mono flex justify-between">
         <span>Architecture Ready: Omium.Trace.v1</span>
         <span>Observability Level: Operational</span>
      </div>
    </div>
  );
};

export default OrchestrationTrace;
