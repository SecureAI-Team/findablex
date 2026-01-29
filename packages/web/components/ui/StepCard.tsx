import { cn } from '@/lib/utils';

interface StepCardProps {
  number: number;
  title: string;
  description: string;
  isLast?: boolean;
  className?: string;
}

export function StepCard({
  number,
  title,
  description,
  isLast = false,
  className,
}: StepCardProps) {
  return (
    <div className={cn('relative flex flex-col items-center text-center', className)}>
      {/* Connector Line */}
      {!isLast && (
        <div className="hidden lg:block absolute top-8 left-[calc(50%+40px)] w-[calc(100%-80px)] h-0.5 bg-gradient-to-r from-primary-500/50 to-accent-500/50" />
      )}

      {/* Number Circle */}
      <div className="relative z-10 w-16 h-16 bg-gradient-to-br from-primary-500 to-accent-500 rounded-full flex items-center justify-center mb-6 shadow-lg shadow-primary-500/25">
        <span className="text-white font-display text-2xl font-bold">{number}</span>
      </div>

      {/* Content */}
      <h3 className="font-display text-lg lg:text-xl font-semibold text-white mb-3">
        {title}
      </h3>
      <p className="text-slate-400 text-sm lg:text-base leading-relaxed max-w-xs">
        {description}
      </p>
    </div>
  );
}
