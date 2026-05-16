import os

app_tsx_content = """import React, { useState, useEffect } from 'react';
import Editor from '@monaco-editor/react';
import { Play, PenTool, Target, TrendingUp, Rocket, Square } from 'lucide-react';

const STRATEGY_TEMPLATES = {
  'rsi': {
    name: 'RSI strategy',
    desc: 'Buy oversold, sell overbought',
    badge: 'RSI',
    badgeColor: 'text-indigo-400 bg-indigo-400/10 border-indigo-400/30',
    code: `# Quantive RSI agent\\n\\nimport pandas_ta as ta\\nfrom quantive.sdk import Agent, Signal\\n\\nclass RSIAgent(Agent):\\n    def __init__(self):\\n        self.period = 14\\n        self.oversold = 30\\n        self.overbought = 70\\n\\n    def on_candle(self, candle, hist):\\n        rsi = ta.rsi(hist['close'], length=self.period)\\n        val = rsi.iloc[-1]\\n\\n        if val < self.oversold:\\n            return Signal.BUY\\n        elif val > self.overbought:\\n            return Signal.SELL\\n        \\n        return Signal.HOLD`
  },
  'momentum': {
    name: 'Momentum agent',
    desc: 'Follow N-day price trend',
    badge: 'Momentum',
    badgeColor: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/30',
    code: `# Quantive Momentum agent\\n\\nimport pandas_ta as ta\\nfrom quantive.sdk import Agent, Signal\\n\\nclass MomentumAgent(Agent):\\n    def __init__(self):\\n        self.ma_period = 50\\n\\n    def on_candle(self, candle, hist):\\n        ma = ta.sma(hist['close'], length=self.ma_period)\\n        current_ma = ma.iloc[-1]\\n\\n        if candle['close'] > current_ma:\\n            return Signal.BUY\\n        elif candle['close'] < current_ma:\\n            return Signal.SELL\\n        \\n        return Signal.HOLD`
  },
  'reversion': {
    name: 'Mean reversion',
    desc: 'Snap back to average',
    badge: 'Reversion',
    badgeColor: 'text-orange-400 bg-orange-400/10 border-orange-400/30',
    code: `# Quantive Mean Reversion\\n\\nimport pandas_ta as ta\\nfrom quantive.sdk import Agent, Signal\\n\\nclass MeanReversionAgent(Agent):\\n    def __init__(self):\\n        self.z_threshold = 2.0\\n\\n    def on_candle(self, candle, hist):\\n        z_score = ta.zscore(hist['close'], length=20).iloc[-1]\\n\\n        if z_score < -self.z_threshold:\\n            return Signal.BUY\\n        elif z_score > self.z_threshold:\\n            return Signal.SELL\\n        \\n        return Signal.HOLD`
  },
  'multi': {
    name: 'Multi-signal',
    desc: 'RSI + volume + volatility',
    badge: 'Multi',
    badgeColor: 'text-pink-400 bg-pink-400/10 border-pink-400/30',
    code: `# Quantive Multi-signal\\n\\nfrom quantive.sdk import Agent, Signal\\n\\nclass MultiAgent(Agent):\\n    def on_candle(self, candle, hist):\\n        # Complex logic goes here\\n        pass`
  }
};

const ROOMS = [
  { id: 'r1', name: 'Workshop', icon: PenTool, label: 'R1' },
  { id: 'r2', name: 'Simulator', icon: Target, label: 'R2' },
  { id: 'r3', name: 'Paper trade', icon: TrendingUp, label: 'R3' },
  { id: 'r4', name: 'Live', icon: Rocket, label: 'R4' },
];

interface SimMetrics {
    backtest_return: number;
    live_return: number;
    slippage_cost: number;
    latency_cost: number;
}

function App() {
  const [activeStrategy, setActiveStrategy] = useState<string>('rsi');
  const [code, setCode] = useState<string>(STRATEGY_TEMPLATES['rsi'].code);
  const [activeRoom, setActiveRoom] = useState('r1');
  const [activeRegime, setActiveRegime] = useState('covid_2020');
  
  const [params, setParams] = useState({ period: 14, oversold: 30, overbought: 70, positionSize: 10 });
  const [activeAsset, setActiveAsset] = useState('BTCUSDT');

  const [simStatus, setSimStatus] = useState<'READY' | 'LOADING' | 'REPLAYING' | 'COMPLETED' | 'FAILED'>('READY');
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [balance, setBalance] = useState<number | null>(null);
  const [simProgress, setSimProgress] = useState<{time: string, price: number, pnl?: number, tradeCount?: number, metrics?: SimMetrics} | null>(null);
  const [lastSignal, setLastSignal] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<any>(null);
  const [trades, setTrades] = useState<any[]>([]);

  // Validation state
  const [validationStatus, setValidationStatus] = useState<'idle'|'valid'|'error'>('idle');
  const [validationMessage, setValidationMessage] = useState<string>('Ready for validation');

  useEffect(() => {
     setValidationStatus('idle');
     setValidationMessage('Unsaved changes');
  }, [code, activeAsset]);

  const handleTemplateLoad = (key: string) => {
    setActiveStrategy(key);
    setCode(STRATEGY_TEMPLATES[key as keyof typeof STRATEGY_TEMPLATES].code);
    if (key === 'rsi') {
       setParams({ period: 14, oversold: 30, overbought: 70, positionSize: 10 });
    }
  };

  const handleParamChange = (key: string, value: string) => {
     const numVal = Number(value);
     setParams(prev => ({...prev, [key]: numVal}));
     
     if (activeStrategy === 'rsi') {
        let newCode = code;
        if (key === 'period') newCode = newCode.replace(/self\\.period\\s*=\\s*\\d+/, `self.period = ${numVal}`);
        if (key === 'oversold') newCode = newCode.replace(/self\\.oversold\\s*=\\s*\\d+/, `self.oversold = ${numVal}`);
        if (key === 'overbought') newCode = newCode.replace(/self\\.overbought\\s*=\\s*\\d+/, `self.overbought = ${numVal}`);
        setCode(newCode);
     }
  };

  const validateStrategy = async () => {
    try {
      setValidationMessage('Validating...');
      const res = await fetch('http://localhost:8000/ws/validate', {
         method: 'POST',
         headers: { 'Content-Type': 'application/json' },
         body: JSON.stringify({ code: code })
      });
      const data = await res.json();
      if (data.status === 'success') {
         setValidationStatus('valid');
         setValidationMessage('RSI agent ready'); // Dynamic based on strategy name ideally
      } else {
         setValidationStatus('error');
         setValidationMessage(data.message);
      }
    } catch(e) {
      setValidationStatus('error');
      setValidationMessage('Connection error during validation');
    }
  };

  const startSimulation = () => {
    if (ws) {
      ws.close();
    }
    setSimStatus('LOADING');
    setMetrics(null);
    setTrades([]);
    
    const socket = new WebSocket('ws://localhost:8000/ws/simulate');
    socket.onopen = () => {
      socket.send(JSON.stringify({
        code: code,
        symbol: activeAsset,
        speed_multiplier: 20.0,
        regime: activeRegime
      }));
    };
    
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'status') {
        setSimStatus(data.status);
      } else if (data.type === 'init') {
        setBalance(data.balance);
      } else if (data.type === 'update') {
        setSimProgress({
          time: data.progress.time,
          price: data.progress.price,
          pnl: data.pnl,
          tradeCount: data.trade_count,
          metrics: data.metrics
        });
        setBalance(data.balance);
        if (data.signal) setLastSignal(data.signal);
        if (data.trade) {
          setTrades(prev => [data.trade, ...prev].slice(0, 10));
        }
      } else if (data.type === 'complete') {
        setMetrics(data.metrics);
        setSimStatus('COMPLETED');
        socket.close();
      } else if (data.type === 'error') {
        console.error("Simulation error:", data.message);
        setSimStatus('FAILED');
        socket.close();
      }
    };
    socket.onclose = () => setSimStatus(prev => prev === 'REPLAYING' || prev === 'LOADING' ? 'READY' : prev);
    setWs(socket);
  };
  
  const stopSimulation = () => {
    if (ws) {
      ws.send(JSON.stringify({ action: "stop" }));
      ws.close();
      setSimStatus('READY');
    }
  };

  const getRegimeName = () => {
     switch(activeRegime) {
        case 'covid_2020': return 'COVID 2020';
        case 'ftx_collapse': return 'FTX collapse';
        case '2008_crisis': return '2008 crisis';
        case '2018_bear': return '2018 bear';
        case 'bull_market': return 'Bull market';
        default: return activeRegime;
     }
  };

  return (
    <div className="flex h-screen bg-[#1e1e1e] text-[#cccccc] font-sans overflow-hidden">
      
      {/* LEFT SIDEBAR (always visible) */}
      <div className="w-[280px] bg-[#252526] border-r border-[#333333] flex flex-col z-10 flex-shrink-0">
        <div className="pt-6 pb-6 px-6 flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
             <PenTool className="w-4 h-4" />
          </div>
          <div>
            <h1 className="text-[16px] font-bold text-white tracking-wide leading-tight">Quantive</h1>
            <div className="text-[11px] text-[#858585]">AI trading infra</div>
          </div>
        </div>
        
        {/* Rooms Menu */}
        <div className="px-4 pb-6">
          <div className="text-[11px] font-bold text-[#858585] mb-3 uppercase tracking-widest px-2">Rooms</div>
          <div className="space-y-1">
            {ROOMS.map(room => (
              <button
                key={room.id}
                onClick={() => setActiveRoom(room.id)}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-none ${
                  activeRoom === room.id 
                    ? 'bg-[#37373d] text-white font-semibold' 
                    : 'text-[#cccccc] hover:bg-[#2a2d2e]'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <room.icon className={`w-[16px] h-[16px] ${activeRoom === room.id ? 'text-white' : 'text-[#858585]'}`} />
                  <span>{room.name}</span>
                </div>
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                  activeRoom === room.id ? 'bg-white text-black' : 'bg-[#1e1e1e] text-[#858585]'
                }`}>
                  {room.label}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* System Menu */}
        <div className="px-4 pb-6 border-t border-[#333333] pt-6 flex-1">
          <div className="text-[11px] font-bold text-[#858585] mb-3 uppercase tracking-widest px-2">System</div>
          <div className="space-y-1">
             <button className="w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm text-[#cccccc] hover:bg-[#2a2d2e]">
                <Target className="w-[16px] h-[16px] text-[#858585]" />
                <span>Decision logs</span>
             </button>
             <button className="w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm text-[#cccccc] hover:bg-[#2a2d2e]">
                <TrendingUp className="w-[16px] h-[16px] text-[#858585]" />
                <span>Anomalies</span>
             </button>
             <button className="w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm text-[#cccccc] hover:bg-[#2a2d2e]">
                <Square className="w-[16px] h-[16px] text-[#858585]" />
                <span>Settings</span>
             </button>
          </div>
        </div>

        <div className="p-4 border-t border-[#333333]">
           <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                 <div className="w-8 h-8 rounded-full bg-white text-black flex items-center justify-center text-xs font-bold">AK</div>
                 <div>
                    <div className="text-[13px] font-bold text-white leading-tight">Arjun K.</div>
                    <div className="text-[11px] text-[#858585]">Free plan</div>
                 </div>
              </div>
              <Square className="w-4 h-4 text-[#858585]" />
           </div>
        </div>
      </div>

      {/* DYNAMIC ROOM CONTENT */}
      {activeRoom === 'r1' && (
         <div className="flex-1 flex flex-col min-w-0 bg-[#1e1e1e]">
           {/* TOP HEADER */}
           <div className="h-[80px] border-b border-[#333333] flex items-center justify-between px-8 flex-shrink-0">
              <div className="flex items-center space-x-3">
                 <PenTool className="w-5 h-5 text-indigo-500" />
                 <h2 className="text-[18px] font-bold text-white">Workshop</h2>
                 <span className="text-[13px] text-[#858585] ml-4 border-l border-[#333] pl-4">Build your trading agent</span>
              </div>
              <div className="flex items-center space-x-4">
                 <button onClick={() => setActiveRoom('r2')} className="flex items-center space-x-2 border border-[#444] bg-[#252526] hover:bg-[#333] text-white px-5 py-2.5 rounded-lg text-[13px] font-semibold transition-none shadow-sm">
                    <Target className="w-4 h-4" />
                    <span>Send to simulator</span>
                 </button>
                 <button onClick={validateStrategy} className="flex items-center space-x-2 border border-[#444] bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 px-5 py-2.5 rounded-lg text-[13px] font-semibold transition-none shadow-sm">
                    <Play className="w-4 h-4" />
                    <span>Run</span>
                 </button>
              </div>
           </div>

           <div className="flex-1 flex min-h-0">
              {/* MIDDLE PANEL - EDITOR */}
              <div className="flex-1 flex flex-col relative bg-[#1e1e1e] border-r border-[#333333]">
                 <div className="flex border-b border-[#333333] bg-[#252526] pt-2 px-2 gap-1">
                    <button className="px-5 py-2.5 text-[13px] font-medium text-white border-b-2 border-indigo-500 bg-[#1e1e1e] rounded-t-lg">strategy.py</button>
                    <button className="px-5 py-2.5 text-[13px] font-medium text-[#858585] hover:text-[#ccc] border-b-2 border-transparent">indicators.py</button>
                 </div>
                 <div className="flex-1 w-full relative pt-4">
                    <Editor
                      height="100%"
                      defaultLanguage="python"
                      theme="vs-dark"
                      value={code}
                      onChange={(value) => setCode(value || '')}
                      options={{ minimap: { enabled: false }, fontSize: 14, fontFamily: "'JetBrains Mono', 'Menlo', 'Monaco', monospace" }}
                    />
                 </div>
                 <div className="h-[40px] border-t border-[#333333] flex items-center px-4 bg-[#252526] text-[12px] text-[#858585]">
                    <div className={`w-2 h-2 rounded-full mr-2 ${validationStatus === 'valid' ? 'bg-emerald-500' : validationStatus === 'error' ? 'bg-red-500' : 'bg-[#666]'}`}></div>
                    <span className={`mr-3 ${validationStatus === 'valid' ? 'text-white' : validationStatus === 'error' ? 'text-red-400' : 'text-[#858585]'}`}>{validationMessage}</span>
                    <span className="mx-2">•</span>
                    <span>{activeAsset}</span>
                    <span className="mx-2">•</span>
                    <span>1d</span>
                    <span className="mx-2">•</span>
                    <span>Python 3.11</span>
                 </div>
              </div>

              {/* RIGHT SIDEBAR - TEMPLATES & PARAMS */}
              <div className="w-[320px] bg-[#1e1e1e] flex flex-col overflow-y-auto custom-scrollbar">
                 {/* Strategy Templates */}
                 <div className="p-6 border-b border-[#333333]">
                    <div className="text-[11px] font-bold text-[#858585] mb-4 uppercase tracking-widest">Strategy Templates</div>
                    <div className="space-y-3">
                       {Object.entries(STRATEGY_TEMPLATES).map(([key, template]) => {
                          const isActive = activeStrategy === key;
                          return (
                            <button
                              key={key}
                              onClick={() => handleTemplateLoad(key)}
                              className={`w-full text-left p-4 rounded-xl transition-none border ${
                                isActive 
                                  ? 'bg-[#252526] border-indigo-500/50' 
                                  : 'bg-[#1e1e1e] border-[#333333] hover:border-[#454545]'
                              }`}
                            >
                              <div className={`text-[14px] font-semibold mb-1 ${isActive ? 'text-white' : 'text-[#cccccc]'}`}>{template.name}</div>
                              <div className="text-[12px] text-[#858585] leading-snug mb-3">{template.desc}</div>
                              <span className={`text-[10px] px-2.5 py-0.5 rounded-full font-semibold border ${template.badgeColor}`}>
                                {template.badge}
                              </span>
                            </button>
                          );
                       })}
                    </div>
                 </div>

                 {/* Parameters */}
                 <div className="p-6 border-b border-[#333333]">
                    <div className="text-[11px] font-bold text-[#858585] mb-4 uppercase tracking-widest">Parameters</div>
                    <div className="space-y-4">
                       <div className="flex items-center justify-between">
                         <span className="text-[13px] text-[#cccccc]">RSI period</span>
                         <input type="number" value={params.period} onChange={e => handleParamChange('period', e.target.value)} className="w-16 h-8 bg-[#252526] border border-[#333333] text-white text-[13px] rounded px-2 focus:outline-none focus:border-indigo-500 text-right" />
                       </div>
                       <div className="flex items-center justify-between">
                         <span className="text-[13px] text-[#cccccc]">Oversold</span>
                         <input type="number" value={params.oversold} onChange={e => handleParamChange('oversold', e.target.value)} className="w-16 h-8 bg-[#252526] border border-[#333333] text-white text-[13px] rounded px-2 focus:outline-none focus:border-indigo-500 text-right" />
                       </div>
                       <div className="flex items-center justify-between">
                         <span className="text-[13px] text-[#cccccc]">Overbought</span>
                         <input type="number" value={params.overbought} onChange={e => handleParamChange('overbought', e.target.value)} className="w-16 h-8 bg-[#252526] border border-[#333333] text-white text-[13px] rounded px-2 focus:outline-none focus:border-indigo-500 text-right" />
                       </div>
                       <div className="flex items-center justify-between">
                         <span className="text-[13px] text-[#cccccc]">Position %</span>
                         <input type="number" value={params.positionSize} onChange={e => handleParamChange('positionSize', e.target.value)} className="w-16 h-8 bg-[#252526] border border-[#333333] text-white text-[13px] rounded px-2 focus:outline-none focus:border-indigo-500 text-right" />
                       </div>
                    </div>
                 </div>

                 {/* Asset */}
                 <div className="p-6">
                    <div className="text-[11px] font-bold text-[#858585] mb-4 uppercase tracking-widest">Asset</div>
                    <div className="flex flex-wrap gap-2">
                       {['BTCUSDT', 'ETHUSDT'].map(asset => (
                         <button 
                           key={asset}
                           onClick={() => setActiveAsset(asset)}
                           className={`text-[12px] px-4 py-1.5 rounded-full border transition-none font-medium ${
                             activeAsset === asset 
                               ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30' 
                               : 'bg-transparent text-[#858585] border-[#333333] hover:border-[#555555]'
                           }`}
                         >
                           {asset}
                         </button>
                       ))}
                    </div>
                 </div>
              </div>
           </div>
         </div>
      )}

      {activeRoom === 'r2' && (
         <div className="flex-1 overflow-y-auto bg-[#1e1e1e] p-10 custom-scrollbar text-[#cccccc]">
            {/* Header */}
            <div className="flex justify-between items-center mb-8 border-b border-[#333] pb-6">
              <div className="flex items-center space-x-3">
                <div className="w-4 h-4 border-2 border-orange-500 rounded-sm"></div>
                <h2 className="text-2xl font-bold text-white">Storm simulator</h2>
                <span className="text-sm text-[#858585] ml-4">{STRATEGY_TEMPLATES[activeStrategy as keyof typeof STRATEGY_TEMPLATES]?.name} — {activeAsset} — {getRegimeName()}</span>
              </div>
              <div className="flex space-x-3 items-center">
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
                    <button onClick={startSimulation} className="flex items-center space-x-2 border border-[#444] bg-[#252526] hover:bg-[#333] text-white px-5 py-2.5 rounded-lg text-sm font-semibold transition-none">
                      <div className="w-3 h-3 border-2 border-white rounded-sm"></div>
                      <span>Run simulation</span>
                    </button>
                  )}
              </div>
            </div>

            {/* Metrics Row */}
            <div className="grid grid-cols-3 gap-6 mb-8">
              <div className="bg-[#252526] border border-[#333333] p-6 rounded-xl">
                <div className="text-[12px] font-bold text-[#858585] uppercase tracking-widest mb-4">Backtest Return</div>
                <div className={`text-4xl font-light mb-2 ${(simProgress?.metrics?.backtest_return || 0) >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>{(simProgress?.metrics?.backtest_return || 0) > 0 ? '+' : ''}{(simProgress?.metrics?.backtest_return || 0).toFixed(1)}%</div>
                <div className="text-[14px] text-[#858585]">On historical data</div>
              </div>
              <div className="bg-[#252526] border border-red-500/30 p-6 rounded-xl shadow-[0_0_15px_rgba(239,68,68,0.05)]">
                <div className="text-[12px] font-bold text-[#858585] uppercase tracking-widest mb-4">Estimated Live Return</div>
                <div className={`text-4xl font-light mb-2 ${(simProgress?.metrics?.live_return || 0) >= 0 ? 'text-orange-500' : 'text-red-500'}`}>{(simProgress?.metrics?.live_return || 0) > 0 ? '+' : ''}{(simProgress?.metrics?.live_return || 0).toFixed(1)}%</div>
                <div className="text-[14px] text-[#858585]">After all friction applied</div>
              </div>
              <div className="bg-[#252526] border border-orange-500/30 p-6 rounded-xl shadow-[0_0_15px_rgba(249,115,22,0.05)]">
                <div className="text-[12px] font-bold text-[#858585] uppercase tracking-widest mb-4">Return Gap</div>
                <div className="text-4xl font-light text-orange-400 mb-2">{((simProgress?.metrics?.live_return || 0) - (simProgress?.metrics?.backtest_return || 0)).toFixed(1)}%</div>
                <div className="text-[14px] text-[#858585]">Where your returns die</div>
              </div>
            </div>

            {/* Middle Section */}
            <div className="grid grid-cols-3 gap-8 mb-8">
                {/* Breakdown */}
                <div className="col-span-2 bg-[#252526] border border-[#333333] rounded-xl p-8">
                  <h3 className="text-[16px] font-bold text-white mb-8">Where your {Math.abs((simProgress?.metrics?.live_return || 0) - (simProgress?.metrics?.backtest_return || 0)).toFixed(1)}% dies</h3>
                  <div className="space-y-5">
                    <div className="flex items-center">
                      <div className="w-[160px] text-[14px] text-white">Backtest return</div>
                      <div className="flex-1 bg-emerald-500/20 h-10 rounded-r flex items-center px-4">
                        <span className="text-[14px] font-bold text-emerald-500">{(simProgress?.metrics?.backtest_return || 0).toFixed(1)}%</span>
                      </div>
                      <div className="w-[80px] text-right text-[14px] text-emerald-500">{(simProgress?.metrics?.backtest_return || 0).toFixed(1)}</div>
                    </div>
                    <div className="flex items-center">
                      <div className="w-[160px] text-[14px] text-white">Slippage cost</div>
                      <div className="flex-1">
                         <div className="bg-red-600/80 h-10 rounded-r flex items-center px-4" style={{width: Math.min(100, Math.max(5, Math.abs((simProgress?.metrics?.slippage_cost || 0)*2))) + '%'}}>
                           <span className="text-[14px] font-bold text-white">{(simProgress?.metrics?.slippage_cost || 0).toFixed(1)}%</span>
                         </div>
                      </div>
                      <div className="w-[80px] text-right text-[14px] text-red-500">{(simProgress?.metrics?.slippage_cost || 0).toFixed(1)}</div>
                    </div>
                    <div className="flex items-center">
                      <div className="w-[160px] text-[14px] text-white">Latency cost</div>
                      <div className="flex-1">
                         <div className="bg-red-600/80 h-10 rounded-r flex items-center px-4" style={{width: Math.min(100, Math.max(5, Math.abs((simProgress?.metrics?.latency_cost || 0)*2))) + '%'}}>
                           <span className="text-[14px] font-bold text-white">{(simProgress?.metrics?.latency_cost || 0).toFixed(1)}%</span>
                         </div>
                      </div>
                      <div className="w-[80px] text-right text-[14px] text-red-500">{(simProgress?.metrics?.latency_cost || 0).toFixed(1)}</div>
                    </div>
                    <div className="flex items-center opacity-50">
                      <div className="w-[160px] text-[14px] text-white">Regime mismatch</div>
                      <div className="flex-1">
                         <div className="bg-orange-500 h-10 rounded-r flex items-center px-4" style={{width: '15%'}}>
                           <span className="text-[14px] font-bold text-white">0%</span>
                         </div>
                      </div>
                      <div className="w-[80px] text-right text-[14px] text-orange-400">0.0</div>
                    </div>
                    <div className="flex items-center opacity-50">
                      <div className="w-[160px] text-[14px] text-white">Market impact</div>
                      <div className="flex-1">
                         <div className="bg-orange-500 h-10 rounded-r flex items-center px-4" style={{width: '8%'}}>
                           <span className="text-[14px] font-bold text-white">0%</span>
                         </div>
                      </div>
                      <div className="w-[80px] text-right text-[14px] text-orange-400">0.0</div>
                    </div>
                    <div className="flex items-center border-t border-[#333] pt-6 mt-4">
                      <div className="w-[160px] text-[14px] text-white">Estimated live</div>
                      <div className="flex-1">
                         <div className="bg-[#6366f1] h-10 rounded-r flex items-center px-4" style={{width: Math.min(100, Math.max(10, Math.abs((simProgress?.metrics?.live_return || 0)*2))) + '%'}}>
                           <span className="text-[14px] font-bold text-white">{(simProgress?.metrics?.live_return || 0).toFixed(1)}%</span>
                         </div>
                      </div>
                      <div className="w-[80px] text-right text-[14px] text-[#6366f1]">{(simProgress?.metrics?.live_return || 0).toFixed(1)}</div>
                    </div>
                  </div>
                </div>
                
                {/* Friction layers & Trades */}
                <div className="flex flex-col space-y-6">
                    <div className="bg-[#252526] border border-[#333333] rounded-xl p-6">
                      <div className="text-[14px] text-white font-bold mb-4">Friction layers</div>
                      <div className="flex flex-wrap gap-2">
                        <div className="px-4 py-1.5 rounded-full border border-orange-500/50 bg-orange-500/10 text-orange-400 text-[12px] font-medium">Slippage</div>
                        <div className="px-4 py-1.5 rounded-full border border-orange-500/50 bg-orange-500/10 text-orange-400 text-[12px] font-medium">Latency</div>
                        <div className="px-4 py-1.5 rounded-full border border-orange-500/50 bg-orange-500/10 text-orange-400 text-[12px] font-medium opacity-50">Regime</div>
                        <div className="px-4 py-1.5 rounded-full border border-[#444] bg-[#222] text-[#888] text-[12px] font-medium">Market impact</div>
                        <div className="px-4 py-1.5 rounded-full border border-[#444] bg-[#222] text-[#888] text-[12px] font-medium">Monte Carlo x1000</div>
                      </div>
                    </div>
                    
                    <div className="bg-[#252526] border border-[#333333] rounded-xl p-6 flex-1 overflow-hidden flex flex-col">
                      <div className="text-[14px] text-white font-bold mb-4 flex justify-between">
                         <span>Live Replay Progress</span>
                         <span className="text-[#858585] font-normal">{simProgress?.time ? new Date(simProgress.time).toLocaleDateString() : '-'}</span>
                      </div>
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-[13px] text-[#858585]">Price</span>
                        <span className="text-[13px] text-white">${simProgress?.price?.toFixed(2) || '-'}</span>
                      </div>
                      <div className="flex justify-between items-center mb-4">
                        <span className="text-[13px] text-[#858585]">Trades</span>
                        <span className="text-[13px] text-white">{simProgress?.tradeCount || 0}</span>
                      </div>
                      <div className="text-[14px] text-white font-bold mb-2">Recent Executions</div>
                      <div className="space-y-2 overflow-y-auto custom-scrollbar flex-1 pr-2">
                          {trades.length === 0 && <div className="text-[#858585] text-xs italic">No trades yet...</div>}
                          {trades.map((t, idx) => (
                            <div key={idx} className="bg-[#1e1e1e] border border-[#333333] rounded px-3 py-2 flex justify-between items-center text-[12px]">
                              <span className={t.signal === 'BUY' ? 'text-emerald-500 font-bold' : 'text-red-500 font-bold'}>{t.signal}</span>
                              <span className="text-white">${t.price.toFixed(2)}</span>
                            </div>
                          ))}
                      </div>
                    </div>
                </div>
            </div>

            {/* Regimes Grid */}
            <div className="grid grid-cols-4 gap-6">
              <div onClick={() => setActiveRegime('covid_2020')} className={`cursor-pointer bg-[#252526] border p-5 rounded-xl ${activeRegime === 'covid_2020' ? 'border-[#666]' : 'border-[#333]'}`}>
                <div className="flex justify-between items-center mb-3">
                   <span className="text-[14px] text-white font-bold">COVID 2020</span>
                   {activeRegime === 'covid_2020' && <span className="bg-orange-500/20 text-orange-400 text-[10px] px-2 py-0.5 rounded-full uppercase font-bold tracking-wider">active</span>}
                </div>
                <div className="text-2xl font-light text-orange-500 mb-1">+11.4%</div>
                <div className="text-[12px] text-[#858585]">live estimate</div>
              </div>
              
              <div onClick={() => setActiveRegime('ftx_collapse')} className={`cursor-pointer bg-[#252526] border p-5 rounded-xl ${activeRegime === 'ftx_collapse' ? 'border-[#666]' : 'border-[#333]'}`}>
                <div className="flex justify-between items-center mb-3">
                   <span className="text-[14px] text-white font-bold">FTX collapse</span>
                   {activeRegime === 'ftx_collapse' && <span className="bg-orange-500/20 text-orange-400 text-[10px] px-2 py-0.5 rounded-full uppercase font-bold tracking-wider">active</span>}
                </div>
                <div className="text-2xl font-light text-red-500 mb-1">-4.2%</div>
                <div className="text-[12px] text-[#858585]">live estimate</div>
              </div>

              <div onClick={() => setActiveRegime('2008_crisis')} className={`cursor-pointer bg-[#252526] border p-5 rounded-xl ${activeRegime === '2008_crisis' ? 'border-[#666]' : 'border-[#333]'}`}>
                <div className="flex justify-between items-center mb-3">
                   <span className="text-[14px] text-white font-bold">2008 crisis</span>
                   {activeRegime === '2008_crisis' && <span className="bg-orange-500/20 text-orange-400 text-[10px] px-2 py-0.5 rounded-full uppercase font-bold tracking-wider">active</span>}
                </div>
                <div className="text-2xl font-light text-orange-500 mb-1">+6.1%</div>
                <div className="text-[12px] text-[#858585]">live estimate</div>
              </div>

              <div className="bg-[#252526] border border-[#333] p-5 rounded-xl flex flex-col items-center justify-center row-span-2">
                <div className="text-[12px] font-bold text-[#858585] uppercase tracking-widest mb-3">ROBUSTNESS</div>
                <div className="text-4xl font-light text-orange-500 mb-3">54/100</div>
                <div className="text-[13px] text-orange-500 flex items-center font-bold"><span className="mr-2">⚠</span> moderate</div>
              </div>
              
              <div onClick={() => setActiveRegime('2018_bear')} className={`cursor-pointer bg-[#252526] border p-5 rounded-xl ${activeRegime === '2018_bear' ? 'border-[#666]' : 'border-[#333]'}`}>
                <div className="flex justify-between items-center mb-3">
                   <span className="text-[14px] text-white font-bold">2018 bear</span>
                   {activeRegime === '2018_bear' && <span className="bg-orange-500/20 text-orange-400 text-[10px] px-2 py-0.5 rounded-full uppercase font-bold tracking-wider">active</span>}
                </div>
                <div className="text-2xl font-light text-emerald-500 mb-1">+18.3%</div>
                <div className="text-[12px] text-[#858585]">live estimate</div>
              </div>

              <div onClick={() => setActiveRegime('bull_market')} className={`cursor-pointer bg-[#252526] border p-5 rounded-xl ${activeRegime === 'bull_market' ? 'border-[#666]' : 'border-[#333]'}`}>
                <div className="flex justify-between items-center mb-3">
                   <span className="text-[14px] text-white font-bold">Bull market</span>
                   {activeRegime === 'bull_market' && <span className="bg-orange-500/20 text-orange-400 text-[10px] px-2 py-0.5 rounded-full uppercase font-bold tracking-wider">active</span>}
                </div>
                <div className="text-2xl font-light text-emerald-500 mb-1">+24.1%</div>
                <div className="text-[12px] text-[#858585]">live estimate</div>
              </div>
            </div>

         </div>
      )}

      {(activeRoom === 'r3' || activeRoom === 'r4') && (
         <div className="flex-1 flex items-center justify-center bg-[#1e1e1e]">
            <div className="text-[#858585] text-lg font-light tracking-wide">{activeRoom === 'r3' ? 'Paper trade' : 'Live'} infrastructure coming soon...</div>
         </div>
      )}

    </div>
  );
}

export default App;
"""

with open("/Users/rohitdiliplahare/Desktop/QUANT_RL/frontend/src/App.tsx", "w") as f:
    f.write(app_tsx_content)

print("Updated App.tsx")
