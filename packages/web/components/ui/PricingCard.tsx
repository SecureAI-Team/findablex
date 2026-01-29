import Link from 'next/link';
import { Check } from 'lucide-react';
import { cn } from '@/lib/utils';

interface PricingCardProps {
  name: string;
  description: string;
  price: number | string;
  period?: string;
  features: string[];
  cta: string;
  ctaHref: string;
  popular?: boolean;
  className?: string;
}

export function PricingCard({
  name,
  description,
  price,
  period = '/月',
  features,
  cta,
  ctaHref,
  popular = false,
  className,
}: PricingCardProps) {
  return (
    <div
      className={cn(
        'relative rounded-2xl p-6 lg:p-8 border transition-all duration-300',
        popular
          ? 'bg-gradient-to-b from-primary-500/10 to-accent-500/10 border-primary-500/50 scale-105 shadow-xl shadow-primary-500/10'
          : 'bg-slate-800/50 border-slate-700/50 hover:border-slate-600',
        className
      )}
    >
      {/* Popular Badge */}
      {popular && (
        <div className="absolute -top-4 left-1/2 -translate-x-1/2">
          <span className="bg-gradient-to-r from-primary-500 to-accent-500 text-white text-xs font-semibold px-4 py-1.5 rounded-full shadow-lg">
            最受欢迎
          </span>
        </div>
      )}

      {/* Header */}
      <div className="text-center mb-6">
        <h3 className="font-display text-xl lg:text-2xl font-bold text-white mb-2">
          {name}
        </h3>
        <p className="text-slate-400 text-sm">{description}</p>
      </div>

      {/* Price */}
      <div className="text-center mb-8">
        <div className="flex items-end justify-center gap-1">
          {typeof price === 'number' && price > 0 && (
            <span className="text-slate-400 text-lg">¥</span>
          )}
          <span className="font-display text-4xl lg:text-5xl font-bold text-white">
            {typeof price === 'number' && price === 0 ? '免费' : price}
          </span>
          {typeof price === 'number' && price > 0 && (
            <span className="text-slate-400 text-base mb-1">{period}</span>
          )}
        </div>
      </div>

      {/* Features */}
      <ul className="space-y-4 mb-8">
        {features.map((feature, index) => (
          <li key={index} className="flex items-start gap-3">
            <div className="w-5 h-5 rounded-full bg-primary-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
              <Check className="w-3 h-3 text-primary-400" />
            </div>
            <span className="text-slate-300 text-sm">{feature}</span>
          </li>
        ))}
      </ul>

      {/* CTA */}
      <Link
        href={ctaHref}
        className={cn(
          'block w-full py-3 px-6 rounded-lg text-center font-medium transition-all',
          popular
            ? 'bg-gradient-to-r from-primary-500 to-accent-500 text-white hover:shadow-lg hover:shadow-primary-500/25'
            : 'bg-slate-700 text-white hover:bg-slate-600'
        )}
      >
        {cta}
      </Link>
    </div>
  );
}
