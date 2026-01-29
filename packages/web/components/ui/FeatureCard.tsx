import { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface FeatureCardProps {
  icon: LucideIcon;
  title: string;
  description: string;
  className?: string;
}

export function FeatureCard({
  icon: Icon,
  title,
  description,
  className,
}: FeatureCardProps) {
  return (
    <div
      className={cn(
        'group bg-slate-800/50 rounded-2xl p-6 lg:p-8 border border-slate-700/50',
        'hover:border-primary-500/50 hover:bg-slate-800/80',
        'transition-all duration-300 hover:-translate-y-1',
        className
      )}
    >
      <div className="w-12 h-12 lg:w-14 lg:h-14 bg-gradient-to-br from-primary-500/20 to-accent-500/20 rounded-xl flex items-center justify-center mb-5 group-hover:scale-110 transition-transform duration-300">
        <Icon className="w-6 h-6 lg:w-7 lg:h-7 text-primary-400" />
      </div>
      <h3 className="font-display text-lg lg:text-xl font-semibold text-white mb-3">
        {title}
      </h3>
      <p className="text-slate-400 text-sm lg:text-base leading-relaxed">
        {description}
      </p>
    </div>
  );
}
