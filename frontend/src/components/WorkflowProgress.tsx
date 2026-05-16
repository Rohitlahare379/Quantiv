import React from 'react';
import { CheckCircle2, Circle, Activity, ShieldCheck, Rocket } from 'lucide-react';

interface WorkflowProgressProps {
  currentStep: 'EDITING' | 'VALIDATED' | 'SIMULATING' | 'SIMULATED' | 'EVALUATING' | 'EVALUATED';
}

const STEPS = [
  { id: 'EDITING', label: 'Strategy Engineering', icon: Circle },
  { id: 'VALIDATED', label: 'Validated', icon: CheckCircle2 },
  { id: 'SIMULATING', label: 'Storm Simulation', icon: Activity },
  { id: 'SIMULATED', label: 'Performance Verified', icon: ShieldCheck },
  { id: 'EVALUATING', label: 'Autonomous Evaluation', icon: Rocket },
];

const WorkflowProgress: React.FC<WorkflowProgressProps> = ({ currentStep }) => {
  const getStepIndex = (step: string) => STEPS.findIndex(s => s.id === step);
  const currentIndex = getStepIndex(currentStep);

  return (
    <div className="h-14 border-b border-[#333] bg-[#1e1e1e] flex items-center px-10 space-x-8 overflow-x-auto no-scrollbar">
      {STEPS.map((step, index) => {
        const isCompleted = index < currentIndex || (currentStep === 'SIMULATED' && index <= 3) || (currentStep === 'EVALUATED' && index <= 4);
        const isActive = currentStep === step.id || (currentStep === 'SIMULATED' && index === 3);
        const Icon = step.icon;

        return (
          <div key={step.id} className="flex items-center space-x-3 shrink-0">
            <div className={`flex items-center justify-center w-6 h-6 rounded-full border ${
              isCompleted ? 'bg-indigo-500 border-indigo-500 text-white' :
              isActive ? 'border-indigo-400 text-indigo-400 animate-pulse' :
              'border-[#444] text-[#444]'
            }`}>
              {isCompleted ? <CheckCircle2 className="w-4 h-4" /> : isActive ? <Icon className="w-3.5 h-3.5" /> : <div className="text-[10px] font-bold">{index + 1}</div>}
            </div>
            <span className={`text-[11px] font-bold uppercase tracking-widest ${
              isCompleted ? 'text-white' :
              isActive ? 'text-indigo-400' :
              'text-[#555]'
            }`}>
              {step.label}
            </span>
            {index < STEPS.length - 1 && (
              <div className={`w-8 h-px ml-4 ${index < currentIndex ? 'bg-indigo-500' : 'bg-[#333]'}`}></div>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default WorkflowProgress;
