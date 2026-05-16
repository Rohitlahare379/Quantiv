import React from 'react';
import { Square } from 'lucide-react';

interface SimulatorProps {
  activeStrategy: string;
  STRATEGY_TEMPLATES: any;
  activeAsset: string;
  activeRegime: string;
  setActiveRegime: (r: string) => void;
  customStart: string;
  setCustomStart: (d: string) => void;
  customEnd: string;
  setCustomEnd: (d: string) => void;
  getRegimeName: () => string;
  simStatus: string;
  validationStatus: string;
  startSimulation: () => void;
  stopSimulation: () => void;
  simProgress: any;
  metrics: any;
  trades: any[];
  simLogs: any[];
}

const Simulator: React.FC<SimulatorProps> = ({
  activeStrategy, STRATEGY_TEMPLATES, activeAsset, activeRegime, setActiveRegime,
  customStart, setCustomStart, customEnd, setCustomEnd, getRegimeName,
  simStatus, validationStatus, startSimulation, stopSimulation,
  simProgress, metrics, simLogs
}) => {
  const currentPrice = simProgress?.progress?.price ?? simProgress?.price ?? 0;
  const simMetrics = simProgress?.metrics || metrics || {};
  const backtestReturn = simMetrics?.backtest_return ?? 0;
  const liveReturn = simMetrics?.live_return ?? simMetrics?.total_return ?? 0;
  const slippageCost = simMetrics?.slippage_cost ?? 0;
  const latencyCost = simMetrics?.latency_cost ?? 0;
  const tradeCount = metrics?.trade_count ?? simProgress?.trade_count ?? 0;

  const REGIMES = [
    { id: 'full_history', name: 'Full Market Cycle', icon: '🌐' },
    { id: 'covid_2020', name: 'COVID Crash', icon: '📉' },
    { id: 'ftx_collapse', name: 'FTX Collapse', icon: '💥' },
    { id: '2018_bear', name: '2018 Bear Market', icon: '🐻' },
    { id: 'bull_market', name: 'Bull Run 2021', icon: '🐂' },
    { id: 'custom', name: 'Custom Range', icon: '⚙️' },
  ];

  return (
    <div className="flex-1 overflow-y-auto bg-[#1e1e1e] p-10 custom-scrollbar text-[#cccccc]">
      {/* Header */}
      <div className="flex justify-between items-center mb-8 border-b border-[#333] pb-6">
        <div className="flex items-center space-x-3">
          <div className="w-4 h-4 border-2 border-orange-500 rounded-sm"></div>
          <h2 className="text-2xl font-bold text-white">Storm simulator</h2>
          <span className="text-sm text-[#858585] ml-4">{STRATEGY_TEMPLATES[activeStrategy]?.name || 'Custom Strategy'} — {activeAsset} — {getRegimeName()}</span>
        </div>
        <div className="flex space-x-3 items-center">
            <div className="text-sm text-[#858585] mr-4 flex items-center space-x-2 border-r border-[#333] pr-4">
              <span className="uppercase tracking-widest text-[11px] font-bold">Readiness:</span>
              <span className={`text-[11px] font-bold px-2 py-0.5 rounded uppercase ${
                validationStatus === 'valid' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-red-500/10 text-red-500'
              }`}>
                {validationStatus === 'valid' ? 'VALID' : 'INVALID'}
              </span>
            </div>
            <div className="text-sm text-[#858585] mr-4 flex items-center space-x-2">
              <span className="uppercase tracking-widest text-[11px] font-bold">Status:</span>
              <span className={`font-semibold ${simStatus === 'REPLAYING' ? 'text-emerald-400' : simStatus === 'LOADING' ? 'text-blue-400' : simStatus === 'FAILED' ? 'text-red-400' : 'text-white'}`}>{simStatus}</span>
            </div>
            {simStatus === 'REPLAYING' || simStatus === 'LOADING' ? (
              <button onClick={stopSimulation} className="flex items-center space-x-2 border border-[#444] bg-[#252526] hover:bg-[#333] text-white px-5 py-2.5 rounded-lg text-sm font-semibold transition-none">
                <Square className="w-4 h-4" fill="currentColor" />
                <span>Stop simulation</span>
              </button>
            ) : (
              <button 
                onClick={startSimulation} 
                disabled={validationStatus !== 'valid'}
                className={`flex items-center space-x-2 border border-[#444] px-5 py-2.5 rounded-lg text-sm font-semibold transition-none ${
                  validationStatus === 'valid' 
                    ? 'bg-[#252526] hover:bg-[#333] text-white' 
                    : 'bg-[#1a1a1b] text-[#555] cursor-not-allowed opacity-50'
                }`}
              >
                <div className={`w-3 h-3 border-2 rounded-sm ${validationStatus === 'valid' ? 'border-white' : 'border-[#444]'}`}></div>
                <span>{validationStatus === 'valid' ? 'Run simulation' : 'Validation required'}</span>
              </button>
            )}
        </div>
      </div>

      {/* Data Layer Configuration */}
      <div className="bg-[#252526] border border-[#333333] rounded-xl p-6 mb-8">
        <h3 className="text-[12px] font-bold text-[#858585] uppercase tracking-widest mb-6">Data Layer Configuration</h3>
        <div className="grid grid-cols-6 gap-4 mb-6">
          {REGIMES.map(regime => (
            <button
              key={regime.id}
              onClick={() => setActiveRegime(regime.id)}
              className={`p-4 rounded-xl border transition-all ${
                activeRegime === regime.id 
                  ? 'bg-orange-500/10 border-orange-500/50 text-white' 
                  : 'bg-[#1e1e1e] border-[#333] text-[#555] hover:border-[#444]'
              }`}
            >
              <div className="text-xl mb-2">{regime.icon}</div>
              <div className="text-[11px] font-bold uppercase tracking-tight">{regime.name}</div>
            </button>
          ))}
        </div>

        {activeRegime === 'custom' && (
          <div className="grid grid-cols-2 gap-6 p-6 bg-[#1e1e1e] rounded-xl border border-[#333] animate-in fade-in slide-in-from-top-4 duration-300">
            <div>
              <label className="block text-[11px] font-bold text-[#555] uppercase tracking-widest mb-2">Start Date</label>
              <input 
                type="date" 
                value={customStart}
                onChange={(e) => setCustomStart(e.target.value)}
                className="w-full bg-[#252526] border border-[#333] rounded-lg p-3 text-white focus:outline-none focus:border-orange-500/50"
              />
            </div>
            <div>
              <label className="block text-[11px] font-bold text-[#555] uppercase tracking-widest mb-2">End Date</label>
              <input 
                type="date" 
                value={customEnd}
                onChange={(e) => setCustomEnd(e.target.value)}
                className="w-full bg-[#252526] border border-[#333] rounded-lg p-3 text-white focus:outline-none focus:border-orange-500/50"
              />
            </div>
          </div>
        )}
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-4 gap-6 mb-8">
        <div className="bg-[#252526] border border-[#333333] p-6 rounded-xl">
          <div className="text-[12px] font-bold text-[#858585] uppercase tracking-widest mb-4">Backtest Return</div>
          <div className={`text-4xl font-light mb-2 ${backtestReturn >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>{backtestReturn > 0 ? '+' : ''}{backtestReturn.toFixed(1)}%</div>
          <div className="text-[14px] text-[#858585]">On historical data</div>
        </div>
        <div className="bg-[#252526] border border-red-500/30 p-6 rounded-xl shadow-[0_0_15px_rgba(239,68,68,0.05)]">
          <div className="text-[12px] font-bold text-[#858585] uppercase tracking-widest mb-4">Estimated Live Return</div>
          <div className={`text-4xl font-light mb-2 ${liveReturn >= 0 ? 'text-orange-500' : 'text-red-500'}`}>{liveReturn > 0 ? '+' : ''}{liveReturn.toFixed(1)}%</div>
          <div className="text-[14px] text-[#858585]">After all friction applied</div>
        </div>
        <div className="bg-[#252526] border border-[#333] p-6 rounded-xl">
          <div className="text-[12px] font-bold text-[#858585] uppercase tracking-widest mb-4">Win Rate</div>
          <div className="text-4xl font-light text-white mb-2">{metrics?.win_rate ? (metrics.win_rate).toFixed(1) : '0.0'}%</div>
          <div className="text-[14px] text-[#858585]">{tradeCount} closed trades</div>
        </div>
        <div className="bg-[#252526] border border-[#333] p-6 rounded-xl">
          <div className="text-[12px] font-bold text-[#858585] uppercase tracking-widest mb-4">Sharpe Ratio</div>
          <div className="text-4xl font-light text-indigo-400 mb-2">{metrics?.sharpe_ratio?.toFixed(2) || '0.00'}</div>
          <div className="text-[14px] text-[#858585]">Risk-adjusted return</div>
        </div>
      </div>

      {/* Middle Section */}
      <div className="grid grid-cols-3 gap-8 mb-8">
          {/* Breakdown */}
          <div className="col-span-2 bg-[#252526] border border-[#333333] rounded-xl p-8">
            <div className="flex justify-between items-center mb-8">
              <h3 className="text-[16px] font-bold text-white">Where your {Math.abs(liveReturn - backtestReturn).toFixed(1)}% dies</h3>
              <div className="text-sm text-[#858585]">
                Current Price: <span className="text-white font-mono">${currentPrice.toFixed(2)}</span>
              </div>
            </div>
            <div className="space-y-5">
              <div className="flex items-center">
                <div className="w-[160px] text-[14px] text-white">Backtest return</div>
                <div className="flex-1 bg-emerald-500/20 h-10 rounded-r flex items-center px-4">
                  <span className="text-[14px] font-bold text-emerald-500">{backtestReturn.toFixed(1)}%</span>
                </div>
                <div className="w-[80px] text-right text-[14px] text-emerald-500">{backtestReturn.toFixed(1)}</div>
              </div>
              <div className="flex items-center">
                <div className="w-[160px] text-[14px] text-white">Slippage cost</div>
                <div className="flex-1">
                   <div className="bg-red-600/80 h-10 rounded-r flex items-center px-4" style={{width: Math.min(100, Math.max(5, Math.abs(slippageCost * 2))) + '%'}}>
                     <span className="text-[14px] font-bold text-white">{slippageCost.toFixed(1)}%</span>
                   </div>
                </div>
                <div className="w-[80px] text-right text-[14px] text-red-500">{slippageCost.toFixed(1)}</div>
              </div>
              <div className="flex items-center">
                <div className="w-[160px] text-[14px] text-white">Latency cost</div>
                <div className="flex-1">
                   <div className="bg-red-600/80 h-10 rounded-r flex items-center px-4" style={{width: Math.min(100, Math.max(5, Math.abs(latencyCost * 2))) + '%'}}>
                     <span className="text-[14px] font-bold text-white">{latencyCost.toFixed(1)}%</span>
                   </div>
                </div>
                <div className="w-[80px] text-right text-[14px] text-red-500">{latencyCost.toFixed(1)}</div>
              </div>
            </div>
          </div>

          {/* Signal Feed */}
          <div className="bg-[#252526] border border-[#333333] rounded-xl p-6 flex flex-col h-[320px]">
             <h3 className="text-[12px] font-bold text-[#858585] uppercase tracking-widest mb-4">Signal Monitor</h3>
             <div className="flex-1 overflow-y-auto space-y-3 custom-scrollbar">
                {simLogs.slice(0, 20).map((log, i) => (
                  <div key={i} className="flex items-center justify-between text-[13px] border-b border-[#333] pb-2 last:border-0">
                    <div className="flex items-center space-x-2">
                      <div className={`w-1.5 h-1.5 rounded-full ${log.type === 'trade' ? 'bg-emerald-500' : 'bg-indigo-400'}`}></div>
                      <span className="text-[#858585] font-mono">{log.timestamp.split('T')[1].split('.')[0]}</span>
                    </div>
                    <span className="text-white truncate max-w-[160px]">{log.message}</span>
                  </div>
                ))}
                {simLogs.length === 0 && <div className="text-[#555] text-center mt-20 italic">Awaiting signals...</div>}
             </div>
          </div>
      </div>
    </div>
  );
};

export default Simulator;
