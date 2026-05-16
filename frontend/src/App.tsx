import { useState, useEffect } from 'react';
import { PenTool, Target, TrendingUp, Rocket } from 'lucide-react';
import Workshop from './components/Workshop';
import Simulator from './components/Simulator';
import WorkspaceSidebar from './components/WorkspaceSidebar';
import Orchestrator from './components/Orchestrator';
import WorkflowProgress from './components/WorkflowProgress';

const STRATEGY_TEMPLATES = {
  'rsi': {
    name: 'RSI strategy',
    desc: 'Buy oversold, sell overbought',
    badge: 'RSI',
    badgeColor: 'text-indigo-400 bg-indigo-400/10 border-indigo-400/30',
  },
  'momentum': {
    name: 'Momentum agent',
    desc: 'Follow N-day price trend',
    badge: 'Momentum',
    badgeColor: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/30',
  },
  'reversion': {
    name: 'Mean reversion',
    desc: 'Snap back to average',
    badge: 'Reversion',
    badgeColor: 'text-orange-400 bg-orange-400/10 border-orange-400/30',
  },
  'multi': {
    name: 'Multi-signal',
    desc: 'RSI + volume + volatility',
    badge: 'Multi',
    badgeColor: 'text-pink-400 bg-pink-400/10 border-pink-400/30',
  }
};

const ROOMS = [
  { id: 'r1', name: 'Strategy Workshop (R1)', icon: PenTool, label: 'R1' },
  { id: 'r2', name: 'Storm Simulator (R2)', icon: Target, label: 'R2' },
  { id: 'r3', name: 'Autonomous Evaluation (R3)', icon: TrendingUp, label: 'R3' },
];

interface SimMetrics {
    backtest_return: number;
    live_return: number;
    slippage_cost: number;
    latency_cost: number;
}

function App() {
  const [activeStrategy, setActiveStrategy] = useState<string>('rsi');
  const [code, setCode] = useState<string>('');
  const [activeRoom, setActiveRoom] = useState('r1');
  const [activeRegime, setActiveRegime] = useState('full_history');
  const [customStart, setCustomStart] = useState('2021-01-01');
  const [customEnd, setCustomEnd] = useState('2021-06-01');
  
  const [params, setParams] = useState({ period: 14, oversold: 45, overbought: 55, positionSize: 10 });
  const [activeAsset, setActiveAsset] = useState('BTCUSDT');
  const [activeTimeframe, setActiveTimeframe] = useState('1h');
  
  // Strategy Persistence State
  const [savedStrategies, setSavedStrategies] = useState<any[]>([]);
  const [activeStrategyId, setActiveStrategyId] = useState<number | null>(null);
  const [strategyName, setStrategyName] = useState<string>('RSI strategy');

  const [simStatus, setSimStatus] = useState<'READY' | 'LOADING' | 'REPLAYING' | 'PAUSED' | 'STOPPED' | 'COMPLETED' | 'FAILED'>('READY');
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [, setBalance] = useState<number | null>(null);
  const [simProgress, setSimProgress] = useState<{time: string, price: number, pnl?: number, tradeCount?: number, metrics?: SimMetrics, candles_processed?: number, total_candles?: number, percentage?: number, speed?: number, regime?: string} | null>(null);
  const [metrics, setMetrics] = useState<any>(null);
  const [trades, setTrades] = useState<any[]>([]);
  const [simLogs, setSimLogs] = useState<{timestamp: string, message: string, type: 'trade' | 'status' | 'signal'}[]>([]);

  // Validation state
  const [validationStatus, setValidationStatus] = useState<'idle'|'valid'|'error'>('idle');
  const [validationMessage, setValidationMessage] = useState<string>('Ready for validation');

  // Global Workflow State
  const [workflowStep, setWorkflowStep] = useState<'EDITING' | 'VALIDATED' | 'SIMULATING' | 'SIMULATED' | 'EVALUATING' | 'EVALUATED'>('EDITING');
  const [globalMetrics, setGlobalMetrics] = useState<any>(null);
  const [isDirty, setIsDirty] = useState(false);

  useEffect(() => {
     // Skip setting dirty on initial load if we just loaded a strategy
     if (validationMessage === 'Strategy loaded' || validationMessage === 'Template loaded') {
        return;
     }

     if (validationStatus === 'valid' || workflowStep !== 'EDITING') {
        setValidationStatus('idle');
        setValidationMessage('Unsaved changes');
        setWorkflowStep('EDITING');
        setGlobalMetrics(null);
        setIsDirty(true);
     }
  }, [code, activeAsset, params, activeTimeframe]);

  useEffect(() => {
     fetchStrategies();
     console.log("%c--- Quantive Frontend Initialized ---", "color: #6366f1; font-weight: bold; font-size: 12px;");
     console.log("API Base:", import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000');
     console.log("WebSocket Base:", import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000');
  }, []);

  const fetchStrategies = async () => {
     try {
        const res = await fetch('http://localhost:8000/api/strategies');
        if (res.ok) {
           const data = await res.json();
           setSavedStrategies(data);
        }
     } catch (e) {
        console.error('Failed to fetch strategies:', e);
     }
  };

  const saveStrategy = async (nameOverride?: any) => {
      const nameToSave = (typeof nameOverride === 'string') ? nameOverride : strategyName;
      const url = activeStrategyId 
         ? `http://localhost:8000/api/strategies/${activeStrategyId}`
         : 'http://localhost:8000/api/strategies';
      const method = activeStrategyId ? 'PUT' : 'POST';

      try {
         const res = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
               name: nameToSave,
               code: code,
               template_id: activeStrategy,
               asset: activeAsset,
               timeframe: activeTimeframe,
               parameters: params
            })
         });
         if (res.ok) {
            const data = await res.json();
            setActiveStrategyId(data.id);
            setStrategyName(data.name);
            fetchStrategies();
            setValidationStatus('idle');
            setValidationMessage('Strategy saved');
            setIsDirty(false);
         }
      } catch (e) {
         console.error('Failed to save strategy:', e);
      }
  };

   const loadStrategy = (strategy: any) => {
      setActiveStrategyId(strategy.id);
      setStrategyName(strategy.name);
      setActiveStrategy(strategy.template_id || 'rsi');
      setCode(strategy.code);
      setActiveAsset(strategy.asset || 'BTCUSDT');
      setActiveTimeframe(strategy.timeframe || '1h');
      if (strategy.parameters) {
         setParams(strategy.parameters);
      }
      setValidationStatus('idle');
      setValidationMessage('Strategy loaded');
      setWorkflowStep('EDITING');
      setIsDirty(false);
   };

  const deleteStrategy = async (id: number) => {
     try {
        const res = await fetch(`http://localhost:8000/api/strategies/${id}`, {
           method: 'DELETE'
        });
        if (res.ok) {
           if (activeStrategyId === id) {
              setActiveStrategyId(null);
           }
           fetchStrategies();
        }
     } catch (e) {
        console.error('Failed to delete strategy:', e);
     }
  };

  const validateStrategy = async () => {
    setValidationStatus('idle');
    setValidationMessage('Validating...');
    
    try {
      const res = await fetch('http://localhost:8000/ws/validate/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: code })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setValidationStatus('valid');
        setValidationMessage('Valid');
        setWorkflowStep('VALIDATED');
      } else {
        setValidationStatus('error');
        setValidationMessage(data.message);
      }
    } catch (e) {
      setValidationStatus('error');
      setValidationMessage('Validation server unreachable');
    }
  };

  const startSimulation = () => {
    if (ws) ws.close();
    
    const socket = new WebSocket('ws://localhost:8000/ws/simulate');
    setWs(socket);
    setSimStatus('LOADING');
    setWorkflowStep('SIMULATING');
    setSimLogs([]);
    setTrades([]);
    setMetrics(null);
    setGlobalMetrics(null);
    setSimProgress(null);

    socket.onopen = () => {
      socket.send(JSON.stringify({
        code: code,
        symbol: activeAsset,
        timeframe: activeTimeframe,
        parameters: params,
        speed_multiplier: 20.0,
        regime: activeRegime,
        start_time: customStart + 'T00:00:00Z',
        end_time: customEnd + 'T00:00:00Z'
      }));
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'status') setSimStatus(data.status);
      if (data.type === 'init') setBalance(data.balance);
      if (data.type === 'update') {
          setSimProgress({ ...data.progress, ...data });
          if (data.metrics) {
            setGlobalMetrics((prev: any) => ({ ...(prev || {}), ...data.metrics }));
          }
          setMetrics((prev: any) => ({
            ...(prev || {}),
            ...(data.metrics || {}),
            win_rate: data.win_rate ?? prev?.win_rate,
            trade_count: data.trade_count ?? prev?.trade_count,
          }));
          if (data.signal) {
            setSimLogs(prev => [{
              timestamp: data.progress?.time || new Date().toISOString(),
              message: `SIGNAL ${data.signal} @ ${Number(data.progress?.price || 0).toFixed(2)}`,
              type: 'signal'
            }, ...prev]);
          }
      }
      if (data.type === 'execution') {
          setTrades(prev => [data.record, ...prev]);
          setSimLogs(prev => [{
            timestamp: data.record.timestamp,
            message: `${data.record.signal} ${data.record.quantity.toFixed(4)} @ ${data.record.execution_price.toFixed(2)}`,
            type: 'trade'
          }, ...prev]);
      }
      if (data.type === 'complete') {
          setSimStatus('COMPLETED');
          setMetrics(data.metrics);
          setGlobalMetrics((prev: any) => ({ ...(prev || {}), ...data.metrics }));
          if (data.trades) setTrades(data.trades);
          setWorkflowStep('SIMULATED');
      }
      if (data.type === 'error') {
          setSimStatus('FAILED');
          alert(data.message);
      }
    };
  };

  const stopSimulation = () => {
    if (ws) {
      ws.send(JSON.stringify({ action: 'stop' }));
      setSimStatus('STOPPED');
    }
  };

  const handleTemplateLoad = (id: string) => {
    const template = STRATEGY_TEMPLATES[id as keyof typeof STRATEGY_TEMPLATES];
    setActiveStrategy(id);
    // setCode(''); // Removed to allow code to persist until user manually clears it
    setActiveStrategyId(null);
    setStrategyName(template.name);
    setValidationStatus('idle');
    setValidationMessage('Template loaded');
  };

  const getRegimeName = () => {
     if (activeRegime === 'custom') return `Custom (${customStart} to ${customEnd})`;
     return activeRegime.replace(/_/g, ' ');
  };

  return (
    <div className="flex h-screen bg-[#0d0d0e] text-[#cccccc] font-sans overflow-hidden">
      {/* Sidebar Navigation */}
      <div className="w-20 border-r border-[#333333] flex flex-col items-center py-8 bg-[#1e1e1e]">
        <div className="w-10 h-10 bg-indigo-600 rounded-xl mb-12 flex items-center justify-center text-white font-bold text-xl shadow-lg shadow-indigo-500/20">Q</div>
        <div className="flex flex-col space-y-8 flex-1">
          {ROOMS.map(room => (
            <button 
              key={room.id}
              onClick={() => setActiveRoom(room.id)}
              className={`p-3 rounded-xl transition-all duration-200 group relative ${activeRoom === room.id ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/30' : 'text-[#555] hover:text-[#888]'}`}
            >
              <room.icon className="w-6 h-6" />
              <div className="absolute left-16 bg-[#252526] text-white text-[11px] px-2.5 py-1.5 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none border border-[#444] font-bold tracking-widest shadow-xl">
                {room.name.toUpperCase()}
              </div>
            </button>
          ))}
        </div>
      </div>

      <WorkspaceSidebar 
        savedStrategies={savedStrategies}
        activeStrategyId={activeStrategyId}
        loadStrategy={loadStrategy}
        deleteStrategy={deleteStrategy}
        STRATEGY_TEMPLATES={STRATEGY_TEMPLATES}
        handleTemplateLoad={handleTemplateLoad}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <WorkflowProgress currentStep={workflowStep} />
      {activeRoom === 'r1' && (
        <Workshop 
          strategyName={strategyName}
          setStrategyName={setStrategyName}
          code={code}
          setCode={(nextCode) => setCode(nextCode || '')}
          activeAsset={activeAsset}
          setActiveAsset={setActiveAsset}
          activeTimeframe={activeTimeframe}
          setActiveTimeframe={setActiveTimeframe}
          params={params}
          setParams={setParams}
          validationStatus={validationStatus}
          validationMessage={validationMessage}
          validateStrategy={validateStrategy}
          saveStrategy={saveStrategy}
          setActiveRoom={setActiveRoom}
        />
      )}

      {activeRoom === 'r2' && (
        <Simulator 
          activeStrategy={activeStrategy}
          STRATEGY_TEMPLATES={STRATEGY_TEMPLATES}
          activeAsset={activeAsset}
          activeRegime={activeRegime}
          setActiveRegime={setActiveRegime}
          customStart={customStart}
          setCustomStart={setCustomStart}
          customEnd={customEnd}
          setCustomEnd={setCustomEnd}
          getRegimeName={getRegimeName}
          simStatus={simStatus}
          validationStatus={validationStatus}
          startSimulation={startSimulation}
          stopSimulation={stopSimulation}
          simProgress={simProgress}
          metrics={metrics}
          trades={trades}
          simLogs={simLogs}
        />
      )}

      {activeRoom === 'r3' && (
        <Orchestrator 
          strategyName={strategyName}
          code={code}
          asset={activeAsset}
          timeframe={activeTimeframe}
          params={params}
          globalMetrics={globalMetrics}
          setWorkflowStep={setWorkflowStep}
        />
      )}
      </div>
    </div>
  );
}

export default App;
