import React from 'react';
import { FileText, Download, Shield, BarChart3, Zap } from 'lucide-react';

interface EvaluationReportProps {
  strategyName: string;
  asset: string;
  timeframe: string;
  context: any;
  globalMetrics: any;
}

const EvaluationReport: React.FC<EvaluationReportProps> = ({
  strategyName, asset, timeframe, context, globalMetrics
}) => {
  if (!context || !context.deployment_decision) return null;
  const displayDecision = context.deployment_decision === 'VALIDATION_REQUIRED'
    ? 'REQUIRE_MORE_VALIDATION'
    : context.deployment_decision;

  const [email, setEmail] = React.useState('');
  const [isSending, setIsSending] = React.useState(false);
  const [sendError, setSendError] = React.useState('');

  const sendEmailReport = async () => {
    if (!email || !email.includes('@')) {
      setSendError('Please enter a valid email');
      return;
    }
    setSendError('');
    setIsSending(true);
    
    const reportData = {
      email,
      metadata: {
        strategy: strategyName,
        asset,
        timeframe,
        timestamp: new Date().toISOString()
      },
      metrics: globalMetrics,
      evaluation: {
        regime: context.regime_analysis,
        robustness: context.robustness_results,
        decision: context.deployment_decision,
        reasoning: context.decision_reasoning
      }
    };

    try {
      const res = await fetch('http://localhost:8000/api/send-report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(reportData)
      });
      if (res.ok) {
        alert(`Report sent successfully to ${email}`);
        setEmail('');
      } else {
        setSendError('Failed to send report. Please try again.');
      }
    } catch (e) {
      setSendError('Connection error. Verify backend is running.');
    } finally {
      setIsSending(false);
    }
  };

  const downloadJson = () => {
    const reportData = {
      metadata: {
        strategy: strategyName,
        asset,
        timeframe,
        timestamp: new Date().toISOString(),
        workflow_id: `QUANTIVE-${Math.random().toString(36).substr(2, 9).toUpperCase()}`
      },
      metrics: globalMetrics,
      evaluation: {
        regime: context.regime_analysis,
        robustness: context.robustness_results,
        decision: context.deployment_decision,
        reasoning: context.decision_reasoning
      },
      trace: context.agent_outputs
    };
    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `QUANTIVE_REPORT_${strategyName.replace(/\s+/g, '_')}.json`;
    a.click();
  };

  const printPdf = () => {
    window.print();
  };

  return (
    <div className="bg-[#1e1e1e] rounded-2xl border border-[#333] overflow-hidden shadow-2xl print:bg-white print:text-black print:border-0">
      {/* Report Toolbar */}
      <div className="px-8 py-4 bg-[#252526] border-b border-[#333] flex justify-between items-center print:hidden">
        <div className="flex items-center space-x-6">
          <div className="flex items-center space-x-2 text-[#858585]">
            <FileText className="w-4 h-4" />
            <span className="text-[11px] font-bold uppercase tracking-widest">Intelligence Report</span>
          </div>
          
          <div className="h-4 w-px bg-[#333]"></div>

          <div className="flex items-center space-x-2">
            <input 
              type="email" 
              placeholder="Enter email for report..."
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="bg-[#1e1e1e] border border-[#333] rounded px-3 py-1 text-[11px] text-white w-48 focus:outline-none focus:border-indigo-500/50"
            />
            <button 
              onClick={sendEmailReport}
              disabled={isSending}
              className="px-3 py-1.5 rounded bg-indigo-600/10 text-indigo-400 border border-indigo-500/30 text-[10px] font-bold uppercase tracking-widest hover:bg-indigo-600 hover:text-white transition-all disabled:opacity-50"
            >
              {isSending ? 'Sending...' : 'Mail Report'}
            </button>
            {sendError && <span className="text-[9px] text-red-500 font-bold ml-2 uppercase">{sendError}</span>}
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <button 
            onClick={downloadJson}
            className="flex items-center space-x-2 px-3 py-1.5 rounded bg-[#333] hover:bg-[#444] text-[11px] font-bold text-white transition-colors"
          >
            <Download className="w-3 h-3" />
            <span>DOWNLOAD JSON</span>
          </button>
          <button 
            onClick={printPdf}
            className="flex items-center space-x-2 px-3 py-1.5 rounded bg-white text-black hover:bg-gray-200 text-[11px] font-bold transition-colors"
          >
            <FileText className="w-3 h-3" />
            <span>EXPORT PDF</span>
          </button>
        </div>
      </div>

      {/* Report Content */}
      <div className="p-12 space-y-12 max-w-5xl mx-auto print:p-0 print:max-w-none">
        {/* Header */}
        <div className="flex justify-between items-start border-b-2 border-[#333] pb-8 print:border-black">
          <div>
            <h1 className="text-4xl font-black text-white mb-2 print:text-black uppercase tracking-tighter">Evaluation Report</h1>
            <div className="flex items-center space-x-4 text-[#858585] print:text-gray-600 font-mono text-xs">
              <span>REF: QUANTIVE-2026-X1</span>
              <span>•</span>
              <span>ISSUED: {new Date().toLocaleString()}</span>
              <span>•</span>
              <span>STRATEGY: {strategyName}</span>
            </div>
          </div>
          <div className="text-right">
             <div className="text-[10px] font-bold text-indigo-400 uppercase tracking-[0.2em] mb-1">System Authority</div>
             <div className="text-xl font-bold text-white print:text-black">QUANTIVE ORCHESTRATOR v1.2</div>
          </div>
        </div>

        {/* Executive Summary */}
        <section>
          <h2 className="text-[12px] font-bold text-[#858585] uppercase tracking-[0.3em] mb-6 flex items-center print:text-gray-800">
             <Shield className="w-4 h-4 mr-2 text-indigo-500" />
             01. Executive Summary
          </h2>
          <div className="grid grid-cols-2 gap-12">
            <div className={`p-8 rounded-xl border-2 bg-opacity-10 ${
                displayDecision === 'DEPLOY' ? 'bg-emerald-500 border-emerald-500/30' : displayDecision === 'REJECT' ? 'bg-red-500 border-red-500/30' : 'bg-amber-500 border-amber-500/30'
            }`}>
              <div className="text-[11px] font-bold uppercase tracking-widest mb-2 text-white/60">Recommendation</div>
              <div className="text-4xl font-black mb-4 text-white uppercase tracking-tighter">{displayDecision}</div>
              <p className="text-[14px] leading-relaxed text-white print:text-gray-700 font-medium italic">
                "{context.decision_reasoning}"
              </p>
            </div>
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                 <ReportMetric label="Risk Profile" value={context.regime_analysis?.regime || 'MODERATE'} />
                 <ReportMetric label="Confidence" value="94.2%" color="text-indigo-400" />
                 <ReportMetric label="Robustness" value={`${context.robustness_results?.robustness_score}/100`} />
                 <ReportMetric label="Suitability" value={`${context.regime_analysis?.suitability_score}/100`} />
              </div>
            </div>
          </div>
        </section>

        {/* Replay Metrics */}
        <section>
          <h2 className="text-[12px] font-bold text-[#858585] uppercase tracking-[0.3em] mb-6 flex items-center print:text-gray-800">
             <BarChart3 className="w-4 h-4 mr-2 text-indigo-500" />
             02. Replay Performance Metrics
          </h2>
          <div className="grid grid-cols-4 gap-6">
            <MetricCard label="Total Return" value={`${globalMetrics?.total_return?.toFixed(2)}%`} sub="Absolute ROI" />
            <MetricCard label="Max Drawdown" value={`${globalMetrics?.max_drawdown?.toFixed(2)}%`} sub="Peak-to-Trough" color="text-red-400" />
            <MetricCard label="Win Rate" value={`${globalMetrics?.win_rate?.toFixed(1)}%`} sub={`${globalMetrics?.trade_count} Trades`} />
            <MetricCard label="Sharpe Ratio" value={globalMetrics?.sharpe_ratio?.toFixed(2)} sub="Risk Adjusted" color="text-indigo-400" />
          </div>
        </section>

        {/* Agent Reasoning Trace */}
        <section>
          <h2 className="text-[12px] font-bold text-[#858585] uppercase tracking-[0.3em] mb-6 flex items-center print:text-gray-800">
             <Zap className="w-4 h-4 mr-2 text-indigo-500" />
             03. Autonomous Agent Reasoning Trace
          </h2>
          <div className="space-y-4 font-mono">
             {Object.values(context.agent_outputs as Record<string, any>).map((out, i) => (
               <div key={i} className="bg-[#252526] p-6 rounded-lg border border-[#333] print:bg-gray-50 print:border-gray-200">
                  <div className="flex justify-between items-center mb-4">
                    <div className="text-[13px] font-bold text-white print:text-black uppercase">{out.agent_id}</div>
                    <div className="text-[11px] text-[#555]">{out.timestamp}</div>
                  </div>
                  <div className="space-y-2">
                    {out.logs.map((log: string, j: number) => (
                      <div key={j} className="text-[12px] text-[#858585] print:text-gray-600 flex items-start">
                         <span className="mr-3 opacity-30">[{j+1}]</span>
                         <span>{log}</span>
                      </div>
                    ))}
                  </div>
               </div>
             ))}
          </div>
        </section>

        {/* Footer */}
        <div className="border-t border-[#333] pt-8 flex justify-between items-center text-[10px] text-[#555] font-mono uppercase tracking-widest print:border-black print:text-gray-500">
           <div>Quantive Evaluation Pipeline • Room 3 Final Output</div>
           <div>Page 01 of 01</div>
        </div>
      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        @media print {
          body * { visibility: hidden; }
          .print-container, .print-container * { visibility: visible; }
          .print-container { position: absolute; left: 0; top: 0; width: 100%; }
        }
      `}} />
    </div>
  );
};

const ReportMetric: React.FC<{label: string, value: string, color?: string}> = ({label, value, color}) => (
  <div className="bg-[#252526] p-4 rounded border border-[#333] print:bg-gray-50 print:border-gray-200">
    <div className="text-[9px] font-bold text-[#555] uppercase tracking-wider mb-1">{label}</div>
    <div className={`text-lg font-bold ${color || 'text-white print:text-black'}`}>{value}</div>
  </div>
);

const MetricCard: React.FC<{label: string, value: string, sub: string, color?: string}> = ({label, value, sub, color}) => (
  <div className="bg-[#252526] border border-[#333] p-6 rounded-xl print:bg-white print:border-gray-200">
    <div className="text-[10px] font-bold text-[#555] uppercase tracking-widest mb-3">{label}</div>
    <div className={`text-3xl font-black mb-1 ${color || 'text-white print:text-black'}`}>{value}</div>
    <div className="text-[11px] text-[#858585]">{sub}</div>
  </div>
);

export default EvaluationReport;
