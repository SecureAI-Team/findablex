'use client';

import { useState } from 'react';
import { Chrome, Globe, Copy, Check, ExternalLink } from 'lucide-react';

interface Step {
  step: string;
  title: string;
  description: string;
}

interface InstallGuideProps {
  chromeSteps: Step[];
  firefoxSteps: Step[];
}

export default function InstallGuide({ chromeSteps, firefoxSteps }: InstallGuideProps) {
  const [activeTab, setActiveTab] = useState<'chrome' | 'firefox'>('chrome');
  const [copiedUrl, setCopiedUrl] = useState(false);

  const steps = activeTab === 'chrome' ? chromeSteps : firefoxSteps;
  const extensionUrl = activeTab === 'chrome' ? 'chrome://extensions' : 'about:debugging#/runtime/this-firefox';

  const copyUrl = () => {
    navigator.clipboard.writeText(extensionUrl);
    setCopiedUrl(true);
    setTimeout(() => setCopiedUrl(false), 2000);
  };

  return (
    <section className="py-20 lg:py-32">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <h2 className="font-display text-3xl lg:text-4xl font-bold text-white mb-4">
            安装教程
          </h2>
          <p className="text-slate-400 text-lg">
            选择您的浏览器，按步骤操作即可完成安装
          </p>
        </div>

        {/* Browser tabs */}
        <div className="flex justify-center gap-3 mb-12">
          <button
            onClick={() => setActiveTab('chrome')}
            className={`flex items-center gap-2 px-6 py-3 rounded-xl font-medium text-sm transition-all ${
              activeTab === 'chrome'
                ? 'bg-primary-500 text-white shadow-lg shadow-primary-500/25'
                : 'bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700 border border-slate-700'
            }`}
          >
            <Chrome className="w-5 h-5" />
            Chrome / Edge
          </button>
          <button
            onClick={() => setActiveTab('firefox')}
            className={`flex items-center gap-2 px-6 py-3 rounded-xl font-medium text-sm transition-all ${
              activeTab === 'firefox'
                ? 'bg-primary-500 text-white shadow-lg shadow-primary-500/25'
                : 'bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700 border border-slate-700'
            }`}
          >
            <Globe className="w-5 h-5" />
            Firefox
          </button>
        </div>

        {/* Quick URL copy */}
        <div className="mb-10 bg-slate-800/50 rounded-xl p-4 border border-slate-700/50 flex flex-col sm:flex-row items-center gap-3">
          <div className="flex-1 text-center sm:text-left">
            <span className="text-slate-400 text-sm">
              {activeTab === 'chrome' ? '步骤 2 需要打开的地址：' : '步骤 2 需要打开的地址：'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <code className="bg-slate-900 text-primary-400 px-4 py-2 rounded-lg text-sm font-mono">
              {extensionUrl}
            </code>
            <button
              onClick={copyUrl}
              className="flex items-center gap-1.5 bg-slate-700 hover:bg-slate-600 text-white px-3 py-2 rounded-lg text-sm transition-colors"
            >
              {copiedUrl ? (
                <>
                  <Check className="w-4 h-4 text-green-400" />
                  <span className="text-green-400">已复制</span>
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4" />
                  复制
                </>
              )}
            </button>
          </div>
        </div>

        {/* Steps */}
        <div className="space-y-6">
          {steps.map((item, index) => (
            <div
              key={`${activeTab}-${item.step}`}
              className="flex gap-5 items-start bg-slate-800/30 rounded-xl p-6 border border-slate-700/30 hover:border-primary-500/20 transition-all"
            >
              <div className="flex-shrink-0 w-12 h-12 bg-primary-500/20 rounded-full flex items-center justify-center border border-primary-500/30">
                <span className="text-primary-400 font-bold text-lg">{item.step}</span>
              </div>
              <div className="pt-0.5">
                <h3 className="text-white font-semibold text-lg mb-1.5">{item.title}</h3>
                <p className="text-slate-400 leading-relaxed">{item.description}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Tip box */}
        <div className="mt-10 bg-amber-500/5 border border-amber-500/20 rounded-xl p-5">
          <div className="flex items-start gap-3">
            <span className="text-amber-400 text-lg mt-0.5">💡</span>
            <div>
              <p className="text-amber-300 font-medium text-sm mb-1">提示</p>
              <p className="text-slate-400 text-sm leading-relaxed">
                {activeTab === 'chrome'
                  ? '通过"加载已解压的扩展程序"安装的插件，在浏览器更新后仍然会保留。您也可以固定插件图标：右键浏览器工具栏 → 固定 FindableX 插件。后续我们将发布到 Chrome Web Store，届时可一键安装和自动更新。'
                  : 'Firefox 临时载入的附加组件在浏览器重启后会失效。后续我们将发布到 Firefox Add-ons 商店，届时可永久安装。'}
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
