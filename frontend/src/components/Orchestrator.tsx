import React, { useMemo, useState } from 'react';
import {
  Activity,
  AlertCircle,
  BarChart3,
  CheckCircle2,
  Clock,
  Cpu,
  Database,
  GitBranch,
  Gauge,
  Layers,
  Network,
  Play,
  Scale,
  ShieldAlert,
  ShieldCheck,
  Timer,
  XCircle,
  Zap
} from 'lucide-react';
import EvaluationReport from './EvaluationReport';
import OrchestrationTrace from './OrchestrationTrace';

type WorkflowLifecycle =
  | 'IDLE'
  | 'ANALYZING'
  | 'RUNNING_AGENT_1'
  | 'RUNNING_AGENT_2'
  | 'RUNNING_AGENT_3'
  | 'COMPLETED'
  | 'FAILED';

interface AgentOutput {
  agent_id: string;
  timestamp: string;
  status: string;
  data: Record<string, unknown>;
  logs: string[];
}

interface TraceEvent {
  agent_id: string;
  event_type: string;
  stage: string;
  timestamp: string;
  duration_ms?: number;
  data: Record<string, unknown>;
  message: string;
}

interface SharedContext {
  regime_analysis?: Record<string, any>;
  robustness_results?: Record<string, any>;
  deployment_decision?: string;
  decision_reasoning?: string;
  replay_metrics?: Record<string, any>;
  agent_outputs?: Record<string, AgentOutput>;
  traces?: TraceEvent[];
  current_phase?: string;
}

interface OrchestratorProps {
  strategyName: string;
  code: string;
  asset: string;
  timeframe: string;
  params: any;
  globalMetrics: any;
  setWorkflowStep: (step: any) => void;
}

const AGENT_SEQUENCE = [
  { state: 'RUNNING_AGENT_1', id: 'RegimeClassifier', label: 'Regime Agent', detail: 'Market state and fit classification', icon: Zap },
  { state: 'RUNNING_AGENT_2', id: 'RobustnessTester', label: 'Robustness Agent', detail: 'Replay-backed stability and friction review', icon: ShieldCheck },
  { state: 'RUNNING_AGENT_3', id: 'DeploymentDecision', label: 'Decision Agent', detail: 'Operational deployment gate', icon: GitBranch }
] as const;

const Orchestrator: React.FC<OrchestratorProps> = ({
  strategyName, code, asset, timeframe, params, globalMetrics, setWorkflowStep
}) => {
  const [lifecycle, setLifecycle] = useState<WorkflowLifecycle>('IDLE');
  const [context, setContext] = useState<SharedContext | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const isOrchestrating = ['ANALYZING', 'RUNNING_AGENT_1', 'RUNNING_AGENT_2', 'RUNNING_AGENT_3'].includes(lifecycle);
  const decision = normalizeDecision(context?.deployment_decision);
  const traceEvents = context?.traces || [];
  const agentOutputs = context?.agent_outputs || {};

  const evidence = useMemo(() => buildEvidence(globalMetrics, context), [globalMetrics, context]);
  const riskRegister = useMemo(() => buildRiskRegister(context, evidence), [context, evidence]);

  const runOrchestration = async () => {
    setLifecycle('ANALYZING');
    setWorkflowStep('EVALUATING');
    setContext(null);
    setErrorMessage(null);

    const stageTimers = [
      window.setTimeout(() => setLifecycle('RUNNING_AGENT_1'), 300),
      window.setTimeout(() => setLifecycle('RUNNING_AGENT_2'), 1400),
      window.setTimeout(() => setLifecycle('RUNNING_AGENT_3'), 2800)
    ];

    try {
      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const res = await fetch(`${apiBase}/api/orchestrate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          strategy_name: strategyName,
          strategy_code: code,
          asset,
          timeframe,
          parameters: params,
          replay_metrics: globalMetrics
        })
      });

      if (!res.ok) {
        throw new Error(`Orchestration request failed with HTTP ${res.status}`);
      }

      const data = await res.json();
      setContext(data);
      setLifecycle(data?.current_phase?.includes('FAILED') ? 'FAILED' : 'COMPLETED');
      setWorkflowStep(data?.current_phase?.includes('FAILED') ? 'EVALUATING' : 'EVALUATED');
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Unknown orchestration failure';
      setErrorMessage(message);
      setLifecycle('FAILED');
      setWorkflowStep('EVALUATING');
      console.error('Orchestration failed:', e);
    } finally {
      stageTimers.forEach(window.clearTimeout);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto bg-[#18191b] p-6 custom-scrollbar text-[#d4d4d4]">
      <div className="border border-[#303236] bg-[#202124] rounded-lg">
        <div className="px-6 py-5 border-b border-[#303236] flex flex-wrap items-center justify-between gap-4 bg-[#1d1f22]">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <Cpu className="w-5 h-5 text-sky-400" />
              <h2 className="text-xl font-semibold text-white">Autonomous Deployment Intelligence</h2>
              <StatusPill state={lifecycle} />
            </div>
            <div className="flex flex-wrap gap-x-4 gap-y-1 text-[12px] text-[#858585] font-mono">
              <span>ROOM_3</span>
              <span>{strategyName}</span>
              <span>{asset}</span>
              <span>{timeframe}</span>
              <span>{globalMetrics ? 'REPLAY_EVIDENCE_READY' : 'AWAITING_REPLAY_EVIDENCE'}</span>
            </div>
          </div>

          <button
            onClick={runOrchestration}
            disabled={isOrchestrating || !globalMetrics}
            className={`h-10 px-4 rounded-md text-sm font-semibold transition-colors flex items-center gap-2 border ${
              isOrchestrating || !globalMetrics
                ? 'bg-[#25272a] text-[#666] border-[#333] cursor-not-allowed'
                : 'bg-sky-600 hover:bg-sky-500 text-white border-sky-400/20'
            }`}
          >
            {isOrchestrating ? <Activity className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            <span>{!globalMetrics ? 'Simulation evidence required' : isOrchestrating ? 'Workflow running' : 'Run orchestration'}</span>
          </button>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-[1.5fr_1fr] gap-0">
          <div className="p-6 border-r border-[#303236] space-y-6">
            {errorMessage && (
              <div className="border border-red-500/30 bg-red-500/10 rounded-md p-4 text-sm text-red-200">
                {errorMessage}
              </div>
            )}

            <DecisionImpactStrip
              lifecycle={lifecycle}
              decision={decision}
              reasoning={context?.decision_reasoning}
              evidence={evidence}
            />

            <LifecycleRail lifecycle={lifecycle} />

            <section>
              <SectionTitle icon={<Layers className="w-4 h-4" />} title="Agent Outputs" />
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <AgentPanel
                  title="Regime Agent"
                  role="Market State Classifier"
                  agentId="RegimeClassifier"
                  icon={<Zap className="w-4 h-4 text-sky-300" />}
                  lifecycle={lifecycle}
                  activeState="RUNNING_AGENT_1"
                  output={agentOutputs.RegimeClassifier}
                  fields={[
                    ['Regime', context?.regime_analysis?.regime],
                    ['Volatility', formatPercent(context?.regime_analysis?.volatility_score)],
                    ['Trend', formatPercent(context?.regime_analysis?.trend_strength)],
                    ['Suitability', formatScore(context?.regime_analysis?.suitability_score)]
                  ]}
                  reasoning={context?.regime_analysis?.reasoning}
                />
                <AgentPanel
                  title="Robustness Agent"
                  role="Replay Evidence Auditor"
                  agentId="RobustnessTester"
                  icon={<ShieldCheck className="w-4 h-4 text-emerald-300" />}
                  lifecycle={lifecycle}
                  activeState="RUNNING_AGENT_2"
                  output={agentOutputs.RobustnessTester}
                  fields={[
                    ['Score', formatScore(context?.robustness_results?.robustness_score)],
                    ['Overfit Risk', context?.robustness_results?.overfitting_risk],
                    ['Stability', context?.robustness_results?.sharpe_stability],
                    ['Friction', context?.robustness_results?.friction_sensitivity]
                  ]}
                  reasoning={context?.robustness_results?.reasoning || (context?.robustness_results?.max_drawdown_consistency ? `Drawdown consistency: ${context.robustness_results.max_drawdown_consistency}` : undefined)}
                />
                <AgentPanel
                  title="Decision Agent"
                  role="Deployment Gatekeeper"
                  agentId="DeploymentDecision"
                  icon={<GitBranch className="w-4 h-4 text-amber-300" />}
                  lifecycle={lifecycle}
                  activeState="RUNNING_AGENT_3"
                  output={agentOutputs.DeploymentDecision}
                  fields={[
                    ['Decision', decision || 'Pending'],
                    ['Regime Fit', formatScore(context?.regime_analysis?.suitability_score)],
                    ['Robustness', formatScore(context?.robustness_results?.robustness_score)],
                    ['Live Gap', evidence.liveVsIdealGap]
                  ]}
                  reasoning={context?.decision_reasoning}
                />
              </div>
            </section>

            <section>
              <SectionTitle icon={<BarChart3 className="w-4 h-4" />} title="SharedContext Evidence" />
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
                <EvidenceTile label="Replay Return" value={evidence.replayReturn} sub="Live portfolio result" />
                <EvidenceTile label="Friction Degradation" value={evidence.frictionDegradation} sub="Slippage + latency drag" tone="warning" />
                <EvidenceTile label="Live vs Ideal Gap" value={evidence.liveVsIdealGap} sub="Execution realism delta" tone="warning" />
                <EvidenceTile label="Max Drawdown" value={evidence.maxDrawdown} sub="Peak-to-trough exposure" tone={evidence.drawdownTone} />
                <EvidenceTile label="Sharpe Ratio" value={evidence.sharpeRatio} sub="Risk-adjusted replay signal" tone={evidence.sharpeTone} />
                <EvidenceTile label="Win Rate" value={evidence.winRate} sub="Executed trade outcomes" />
                <EvidenceTile label="Trade Sample" value={evidence.tradeCount} sub="Replay execution count" />
                <EvidenceTile label="Robustness Evidence" value={evidence.robustnessEvidence} sub="Agent stress result" />
                <EvidenceTile label="Deployment Signal" value={decision || 'IDLE'} sub="Final operational gate" tone={decision === 'REJECT' ? 'danger' : decision === 'DEPLOY' ? 'success' : 'neutral'} />
              </div>
            </section>

            <DeploymentDecisionPanel
              decision={decision}
              reasoning={context?.decision_reasoning}
              regime={context?.regime_analysis}
              robustness={context?.robustness_results}
              evidence={evidence}
              riskRegister={riskRegister}
              lifecycle={lifecycle}
            />
          </div>

          <aside className="p-6 space-y-6 bg-[#1c1d20]">
            <section>
              <SectionTitle icon={<Clock className="w-4 h-4" />} title="Workflow Sequence" />
              <WorkflowTimeline
                lifecycle={lifecycle}
                traces={traceEvents}
                agentOutputs={agentOutputs}
              />
            </section>

            <section>
              <SectionTitle icon={<Gauge className="w-4 h-4" />} title="Operational Metadata" />
              <div className="border border-[#303236] rounded-md divide-y divide-[#303236]">
                <MetaRow label="Backend phase" value={context?.current_phase || lifecycle} />
                <MetaRow label="Trace events" value={String(traceEvents.length)} />
                <MetaRow label="Agent outputs" value={String(Object.keys(agentOutputs).length)} />
                <MetaRow label="Parameters" value={`${Object.keys(params || {}).length} configured`} />
                <MetaRow label="Replay evidence" value={globalMetrics ? 'Available' : 'Missing'} />
              </div>
            </section>

            <section>
              <SectionTitle icon={<Network className="w-4 h-4" />} title="Evidence Substrate" />
              <div className="grid grid-cols-1 gap-3">
                <SubsystemRow icon={<Database className="w-4 h-4" />} label="Replay metrics bus" value={globalMetrics ? 'SYNCHRONIZED' : 'WAITING'} />
                <SubsystemRow icon={<ShieldAlert className="w-4 h-4" />} label="Risk gate status" value={decision || 'NOT_EVALUATED'} />
                <SubsystemRow icon={<GitBranch className="w-4 h-4" />} label="Causality trace" value={traceEvents.length ? `${traceEvents.length} EVENTS` : 'NO_TRACE'} />
              </div>
            </section>
          </aside>
        </div>
      </div>

      <OrchestrationTrace traces={traceEvents} isOrchestrating={isOrchestrating} />

      {context?.deployment_decision && (
        <div className="mt-10">
          <EvaluationReport
            strategyName={strategyName}
            asset={asset}
            timeframe={timeframe}
            context={context}
            globalMetrics={globalMetrics}
          />
        </div>
      )}
    </div>
  );
};

const DecisionImpactStrip: React.FC<{
  lifecycle: WorkflowLifecycle;
  decision?: string;
  reasoning?: string;
  evidence: ReturnType<typeof buildEvidence>;
}> = ({ lifecycle, decision, reasoning, evidence }) => {
  const tone = decision === 'DEPLOY' ? 'border-emerald-500/35 bg-emerald-500/5' : decision === 'REJECT' ? 'border-red-500/35 bg-red-500/5' : decision ? 'border-amber-500/35 bg-amber-500/5' : 'border-[#303236] bg-[#1b1c1f]';
  const label = decision || (lifecycle === 'IDLE' ? 'AWAITING EVIDENCE' : lifecycle);

  return (
    <section className={`border rounded-md ${tone}`}>
      <div className="p-5 grid grid-cols-1 xl:grid-cols-[1fr_auto] gap-5 items-start">
        <div>
          <div className="flex items-center gap-3 mb-3">
            <Scale className="w-5 h-5 text-sky-300" />
            <div>
              <div className="text-[10px] uppercase tracking-[0.22em] text-[#8f949b] font-bold">Deployment impact</div>
              <div className="text-2xl font-black text-white font-mono mt-1">{label}</div>
            </div>
          </div>
          <p className="text-sm text-[#c9c9c9] leading-relaxed max-w-4xl">
            {reasoning || 'Room 3 will render the deployment gate once replay evidence has been injected and the autonomous workflow has completed.'}
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 min-w-[360px]">
          <CompactMetric label="Live return" value={evidence.replayReturn} />
          <CompactMetric label="Friction gap" value={evidence.liveVsIdealGap} />
          <CompactMetric label="Robustness" value={evidence.robustnessEvidence} />
        </div>
      </div>
    </section>
  );
};

const CompactMetric: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div className="border border-[#303236] bg-[#151619] rounded p-3">
    <div className="text-[9px] uppercase tracking-wider text-[#777] mb-1">{label}</div>
    <div className="text-sm font-black font-mono text-white">{value}</div>
  </div>
);

const LifecycleRail: React.FC<{ lifecycle: WorkflowLifecycle }> = ({ lifecycle }) => {
  const states: WorkflowLifecycle[] = ['IDLE', 'ANALYZING', 'RUNNING_AGENT_1', 'RUNNING_AGENT_2', 'RUNNING_AGENT_3', 'COMPLETED', 'FAILED'];
  const labels: Record<WorkflowLifecycle, string> = {
    IDLE: 'Evidence standby',
    ANALYZING: 'Context ingest',
    RUNNING_AGENT_1: 'Regime agent',
    RUNNING_AGENT_2: 'Robustness agent',
    RUNNING_AGENT_3: 'Decision agent',
    COMPLETED: 'Decision locked',
    FAILED: 'Workflow failed'
  };

  return (
    <div className="border border-[#303236] bg-[#1b1c1f] rounded-md p-3">
      <div className="flex items-center justify-between mb-3">
        <div className="text-[10px] uppercase tracking-[0.2em] text-[#777] font-bold">Workflow execution path</div>
        <div className="text-[10px] text-[#666] font-mono">{lifecycle}</div>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-7 gap-2">
      {states.map(state => {
        const active = lifecycle === state;
        const complete = lifecycleIndex(lifecycle) > lifecycleIndex(state) && state !== 'FAILED';
        const failed = lifecycle === 'FAILED' && state === 'FAILED';
        return (
          <div
            key={state}
            className={`min-h-16 rounded-md border px-3 py-3 ${
              active || failed
                ? failed ? 'bg-red-500/10 border-red-500/40' : 'bg-sky-500/10 border-sky-500/40'
                : complete
                  ? 'bg-emerald-500/5 border-emerald-500/20'
                  : 'bg-[#17181b] border-[#303236]'
            }`}
          >
            <div className={`text-[10px] font-mono uppercase leading-tight ${active ? 'text-sky-300' : failed ? 'text-red-300' : complete ? 'text-emerald-300' : 'text-[#666]'}`}>
              {state}
            </div>
            <div className="text-[11px] text-[#a0a0a0] mt-2 leading-tight">{labels[state]}</div>
          </div>
        );
      })}
      </div>
    </div>
  );
};

const AgentPanel: React.FC<{
  title: string;
  role: string;
  agentId: string;
  icon: React.ReactNode;
  lifecycle: WorkflowLifecycle;
  activeState: WorkflowLifecycle;
  output?: AgentOutput;
  fields: Array<[string, React.ReactNode]>;
  reasoning?: string;
}> = ({ title, role, agentId, icon, lifecycle, activeState, output, fields, reasoning }) => {
  const active = lifecycle === activeState;
  const complete = Boolean(output || reasoning);

  return (
    <div className={`border rounded-md bg-[#1b1c1f] ${active ? 'border-sky-500/50' : complete ? 'border-emerald-500/25' : 'border-[#303236]'}`}>
      <div className="px-4 py-3 border-b border-[#303236] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded border border-[#303236] bg-[#151619] flex items-center justify-center">
            {icon}
          </div>
          <div>
            <div className="text-sm font-semibold text-white">{title}</div>
            <div className="text-[10px] text-[#777] font-mono">{agentId}</div>
            <div className="text-[10px] text-[#666] uppercase tracking-wider mt-0.5">{role}</div>
          </div>
        </div>
        {active ? <Activity className="w-4 h-4 text-sky-400 animate-spin" /> : complete ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <Timer className="w-4 h-4 text-[#555]" />}
      </div>

      <div className="p-4 space-y-4">
        <div className="grid grid-cols-2 gap-2">
          {fields.map(([label, value]) => (
            <div key={label} className="bg-[#222326] border border-[#303236] rounded p-3 min-h-16">
              <div className="text-[9px] text-[#777] uppercase tracking-wider mb-1">{label}</div>
              <div className="text-sm font-mono text-[#e6e6e6] break-words">{value ?? 'Pending'}</div>
            </div>
          ))}
        </div>

        <div className="min-h-24 bg-[#151619] border border-[#303236] rounded p-3">
          <div className="text-[9px] text-[#777] uppercase tracking-wider mb-2">Evidence interpretation</div>
          <p className="text-[12px] text-[#b7b7b7] leading-relaxed">{reasoning || 'Awaiting upstream evidence.'}</p>
        </div>

        {output?.logs?.length ? (
          <div className="space-y-1">
            {output.logs.slice(-3).map((log, index) => (
              <div key={`${log}-${index}`} className="text-[11px] text-[#858585] font-mono truncate">event.{index + 1} {log}</div>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
};

const DeploymentDecisionPanel: React.FC<{
  decision?: string;
  reasoning?: string;
  regime?: Record<string, any>;
  robustness?: Record<string, any>;
  evidence: ReturnType<typeof buildEvidence>;
  riskRegister: Array<{ label: string; value: string; tone: 'neutral' | 'warning' | 'danger' | 'success' }>;
  lifecycle: WorkflowLifecycle;
}> = ({ decision, reasoning, regime, robustness, evidence, riskRegister, lifecycle }) => {
  const tone = decision === 'DEPLOY' ? 'emerald' : decision === 'REJECT' ? 'red' : decision ? 'amber' : 'zinc';
  const Icon = decision === 'DEPLOY' ? CheckCircle2 : decision === 'REJECT' ? XCircle : AlertCircle;

  return (
    <section className={`border rounded-md bg-[#1b1c1f] ${tone === 'emerald' ? 'border-emerald-500/35' : tone === 'red' ? 'border-red-500/35' : tone === 'amber' ? 'border-amber-500/35' : 'border-[#303236]'}`}>
      <div className="px-5 py-4 border-b border-[#303236] flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Icon className={`w-5 h-5 ${tone === 'emerald' ? 'text-emerald-400' : tone === 'red' ? 'text-red-400' : tone === 'amber' ? 'text-amber-400' : 'text-[#777]'}`} />
          <div>
            <div className="text-sm font-semibold text-white">Deployment Decision Panel</div>
            <div className="text-[10px] text-[#666] uppercase tracking-wider">Evidence-backed autonomous deployment gate</div>
          </div>
        </div>
        <div className={`px-3 py-1.5 rounded border text-lg font-black font-mono ${
          tone === 'emerald' ? 'border-emerald-500/35 text-emerald-300 bg-emerald-500/10' :
          tone === 'red' ? 'border-red-500/35 text-red-300 bg-red-500/10' :
          tone === 'amber' ? 'border-amber-500/35 text-amber-300 bg-amber-500/10' :
          'border-[#303236] text-white bg-[#151619]'
        }`}>{decision || lifecycle}</div>
      </div>

      <div className="p-5 grid grid-cols-1 xl:grid-cols-[1.1fr_0.9fr] gap-5">
        <div>
          <div className="text-[10px] text-[#777] uppercase tracking-wider mb-2">Structured reasoning</div>
          <div className="bg-[#151619] border border-[#303236] rounded p-4 min-h-32">
            <p className="text-sm text-[#d0d0d0] leading-relaxed">{reasoning || 'No deployment decision has been generated yet.'}</p>
          </div>
        </div>
        <div className="space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <RiskItem label="Deployment rationale" value={buildRationale(decision, regime, robustness)} />
            <RiskItem label="Risk posture" value={buildRisks(regime, robustness, evidence)} />
            <RiskItem label="Evidence basis" value={`${evidence.replayReturn} replay, ${evidence.liveVsIdealGap} live gap`} />
          </div>
          <div className="border border-[#303236] bg-[#151619] rounded p-3">
            <div className="text-[9px] text-[#777] uppercase tracking-wider mb-3">Operational risk register</div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {riskRegister.map(risk => (
                <RiskBadge key={risk.label} {...risk} />
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

const WorkflowTimeline: React.FC<{
  lifecycle: WorkflowLifecycle;
  traces: TraceEvent[];
  agentOutputs: Record<string, AgentOutput>;
}> = ({ lifecycle, traces, agentOutputs }) => {
  if (traces.length > 0) {
    return (
          <div className="border border-[#303236] rounded-md overflow-hidden">
        {traces.map((trace, index) => (
          <div key={`${trace.timestamp}-${index}`} className="px-4 py-3 border-b border-[#303236] last:border-b-0">
            <div className="flex items-center justify-between gap-3 mb-1">
              <span className="text-[11px] text-sky-300 font-mono">#{String(index + 1).padStart(2, '0')} {trace.agent_id}</span>
              <span className="text-[10px] text-[#666] font-mono">{formatTime(trace.timestamp)}</span>
            </div>
            <div className="text-[12px] text-[#d0d0d0]">{trace.message}</div>
            <div className="mt-1 text-[10px] text-[#666] font-mono">
              {trace.event_type} / {trace.stage}{trace.duration_ms ? ` / ${(trace.duration_ms / 1000).toFixed(2)}s` : ''}
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="border border-[#303236] rounded-md divide-y divide-[#303236]">
      {AGENT_SEQUENCE.map(agent => {
        const Icon = agent.icon;
        const active = lifecycle === agent.state;
        const complete = Boolean(agentOutputs[agent.id]);
        return (
          <div key={agent.id} className="px-4 py-3 flex items-center gap-3">
            <Icon className={`w-4 h-4 ${active ? 'text-sky-400' : complete ? 'text-emerald-400' : 'text-[#555]'}`} />
            <div className="flex-1">
              <div className="text-sm text-[#d0d0d0]">{agent.label}</div>
              <div className="text-[10px] text-[#777]">{agent.detail}</div>
              <div className="text-[10px] text-[#666] font-mono mt-1">{complete ? 'Complete' : active ? 'Running' : 'Queued'}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

const EvidenceTile: React.FC<{ label: string; value: string; sub: string; tone?: 'neutral' | 'warning' | 'danger' | 'success' }> = ({
  label, value, sub, tone = 'neutral'
}) => {
  const color = tone === 'danger' ? 'text-red-300' : tone === 'warning' ? 'text-amber-300' : tone === 'success' ? 'text-emerald-300' : 'text-white';
  return (
    <div className="bg-[#1b1c1f] border border-[#303236] rounded-md p-4 min-h-28">
      <div className="text-[10px] text-[#777] uppercase tracking-wider mb-2">{label}</div>
      <div className={`text-lg font-black font-mono ${color}`}>{value}</div>
      <div className="text-[11px] text-[#666] mt-2">{sub}</div>
    </div>
  );
};

const RiskItem: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div className="bg-[#151619] border border-[#303236] rounded p-3">
    <div className="text-[9px] text-[#777] uppercase tracking-wider mb-2">{label}</div>
    <div className="text-[12px] text-[#c8c8c8] leading-relaxed">{value}</div>
  </div>
);

const RiskBadge: React.FC<{ label: string; value: string; tone: 'neutral' | 'warning' | 'danger' | 'success' }> = ({ label, value, tone }) => {
  const cls = tone === 'danger'
    ? 'border-red-500/30 text-red-200 bg-red-500/10'
    : tone === 'warning'
      ? 'border-amber-500/30 text-amber-200 bg-amber-500/10'
      : tone === 'success'
        ? 'border-emerald-500/25 text-emerald-200 bg-emerald-500/10'
        : 'border-[#303236] text-[#c8c8c8] bg-[#1b1c1f]';

  return (
    <div className={`border rounded px-3 py-2 ${cls}`}>
      <div className="text-[9px] uppercase tracking-wider opacity-70">{label}</div>
      <div className="text-[12px] font-mono mt-1">{value}</div>
    </div>
  );
};

const MetaRow: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div className="px-4 py-3 flex items-center justify-between gap-4">
    <span className="text-[10px] text-[#777] uppercase tracking-wider">{label}</span>
    <span className="text-[12px] text-[#d0d0d0] font-mono text-right">{value}</span>
  </div>
);

const SubsystemRow: React.FC<{ icon: React.ReactNode; label: string; value: string }> = ({ icon, label, value }) => (
  <div className="border border-[#303236] bg-[#151619] rounded px-4 py-3 flex items-center justify-between gap-4">
    <div className="flex items-center gap-3">
      <div className="text-[#858585]">{icon}</div>
      <span className="text-[12px] text-[#c8c8c8]">{label}</span>
    </div>
    <span className="text-[10px] text-sky-300 font-mono">{value}</span>
  </div>
);

const SectionTitle: React.FC<{ icon: React.ReactNode; title: string }> = ({ icon, title }) => (
  <div className="flex items-center gap-2 text-[11px] text-[#8f949b] uppercase tracking-[0.18em] font-bold mb-3">
    {icon}
    <span>{title}</span>
  </div>
);

const StatusPill: React.FC<{ state: WorkflowLifecycle }> = ({ state }) => {
  const cls = state === 'COMPLETED'
    ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
    : state === 'FAILED'
      ? 'bg-red-500/10 text-red-300 border-red-500/30'
      : state === 'IDLE'
        ? 'bg-[#2a2c30] text-[#9a9a9a] border-[#3a3d42]'
        : 'bg-sky-500/10 text-sky-300 border-sky-500/30';
  return <span className={`px-2.5 py-1 rounded border text-[10px] font-mono ${cls}`}>{state}</span>;
};

const buildEvidence = (metrics: any, context: SharedContext | null) => {
  const liveReturn = numberOrNull(metrics?.live_return ?? metrics?.total_return);
  const idealReturn = numberOrNull(metrics?.backtest_return);
  const slippage = numberOrNull(metrics?.slippage_cost);
  const latency = numberOrNull(metrics?.latency_cost);
  const drawdown = numberOrNull(metrics?.max_drawdown);
  const sharpe = numberOrNull(metrics?.sharpe_ratio);
  const winRate = numberOrNull(metrics?.win_rate);
  const tradeCount = numberOrNull(metrics?.trade_count);
  const liveGap = liveReturn !== null && idealReturn !== null ? liveReturn - idealReturn : null;
  const friction = slippage !== null || latency !== null ? (slippage || 0) + (latency || 0) : liveGap;

  return {
    replayReturn: formatSignedPercent(liveReturn),
    frictionDegradation: formatSignedPercent(friction),
    liveVsIdealGap: formatSignedPercent(liveGap),
    maxDrawdown: formatPercent(drawdown),
    sharpeRatio: sharpe === null ? 'Pending' : sharpe.toFixed(2),
    winRate: formatPercent(winRate),
    tradeCount: tradeCount === null ? 'Pending' : String(Math.round(tradeCount)),
    robustnessEvidence: context?.robustness_results?.robustness_score !== undefined
      ? `${context.robustness_results.robustness_score}/100`
      : 'Pending',
    slippage: formatSignedPercent(slippage),
    latency: formatSignedPercent(latency),
    drawdownTone: drawdown === null ? 'neutral' as const : drawdown > 35 ? 'danger' as const : drawdown > 20 ? 'warning' as const : 'success' as const,
    sharpeTone: sharpe === null ? 'neutral' as const : sharpe < 0 ? 'danger' as const : sharpe < 0.5 ? 'warning' as const : 'success' as const,
    liveGapRaw: liveGap,
    drawdownRaw: drawdown,
    sharpeRaw: sharpe,
    winRateRaw: winRate,
    tradeCountRaw: tradeCount
  };
};

const buildRationale = (decision?: string, regime?: Record<string, any>, robustness?: Record<string, any>) => {
  if (!decision) return 'Awaiting deployment synthesis.';
  return `${decision} based on ${formatScore(regime?.suitability_score)} regime suitability and ${formatScore(robustness?.robustness_score)} robustness.`;
};

const buildRisks = (regime?: Record<string, any>, robustness?: Record<string, any>, evidence?: ReturnType<typeof buildEvidence>) => {
  const risks = [
    regime?.volatility_score !== undefined ? `volatility ${formatPercent(regime.volatility_score)}` : null,
    robustness?.friction_sensitivity ? `friction sensitivity ${robustness.friction_sensitivity}` : null,
    evidence?.liveVsIdealGap !== 'Pending' ? `live gap ${evidence?.liveVsIdealGap}` : null
  ].filter(Boolean);
  return risks.length ? risks.join(', ') : 'No operational risks rendered yet.';
};

const buildRiskRegister = (context: SharedContext | null, evidence: ReturnType<typeof buildEvidence>) => {
  const regime = context?.regime_analysis;
  const robustness = context?.robustness_results;
  const suitability = numberOrNull(regime?.suitability_score);
  const robustnessScore = numberOrNull(robustness?.robustness_score);
  const volatility = numberOrNull(regime?.volatility_score);

  return [
    {
      label: 'Regime fragility',
      value: suitability === null ? 'Pending' : `${suitability.toFixed(0)}/100 fit`,
      tone: suitability === null ? 'neutral' as const : suitability < 50 ? 'danger' as const : suitability < 70 ? 'warning' as const : 'success' as const
    },
    {
      label: 'Robustness concern',
      value: robustnessScore === null ? 'Pending' : `${robustnessScore.toFixed(0)}/100 score`,
      tone: robustnessScore === null ? 'neutral' as const : robustnessScore < 60 ? 'danger' as const : robustnessScore < 75 ? 'warning' as const : 'success' as const
    },
    {
      label: 'Friction degradation',
      value: evidence.liveVsIdealGap,
      tone: evidence.liveGapRaw === null ? 'neutral' as const : evidence.liveGapRaw < -15 ? 'danger' as const : evidence.liveGapRaw < -5 ? 'warning' as const : 'success' as const
    },
    {
      label: 'Replay sample',
      value: evidence.tradeCount,
      tone: evidence.tradeCountRaw === null ? 'neutral' as const : evidence.tradeCountRaw < 3 ? 'danger' as const : evidence.tradeCountRaw < 10 ? 'warning' as const : 'success' as const
    },
    {
      label: 'Drawdown load',
      value: evidence.maxDrawdown,
      tone: evidence.drawdownTone
    },
    {
      label: 'Volatility state',
      value: volatility === null ? 'Pending' : `${volatility.toFixed(2)}%`,
      tone: volatility === null ? 'neutral' as const : volatility > 80 ? 'warning' as const : 'success' as const
    }
  ];
};

const lifecycleIndex = (state: WorkflowLifecycle) => {
  const order: WorkflowLifecycle[] = ['IDLE', 'ANALYZING', 'RUNNING_AGENT_1', 'RUNNING_AGENT_2', 'RUNNING_AGENT_3', 'COMPLETED', 'FAILED'];
  return order.indexOf(state);
};

const normalizeDecision = (decision?: string) => {
  if (!decision) return undefined;
  if (decision === 'VALIDATION_REQUIRED') return 'REQUIRE_MORE_VALIDATION';
  return decision;
};

const numberOrNull = (value: unknown) => typeof value === 'number' && Number.isFinite(value) ? value : null;
const formatScore = (value: unknown): string => typeof value === 'number' ? `${value}/100` : typeof value === 'string' ? value : 'Pending';
const formatPercent = (value: unknown): string => typeof value === 'number' ? `${value.toFixed(2)}%` : typeof value === 'string' ? value : 'Pending';
const formatSignedPercent = (value: number | null) => value === null ? 'Pending' : `${value > 0 ? '+' : ''}${value.toFixed(2)}%`;
const formatTime = (timestamp?: string) => timestamp ? new Date(timestamp).toLocaleTimeString() : '--:--:--';

export default Orchestrator;
