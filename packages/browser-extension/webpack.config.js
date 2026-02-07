const path = require('path');
const CopyWebpackPlugin = require('copy-webpack-plugin');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const webpack = require('webpack');

module.exports = (env, argv) => {
  const isProduction = argv.mode === 'production';
  const targetBrowser = process.env.BROWSER || 'chrome';

  // Output to browser-specific directory if BROWSER env var is set
  const outputDir = process.env.BROWSER
    ? path.resolve(__dirname, `dist-${targetBrowser}`)
    : path.resolve(__dirname, 'dist');

  // Determine manifest transform for Firefox
  const manifestTransform = (content) => {
    const manifest = JSON.parse(content.toString());

    if (targetBrowser === 'firefox') {
      // Firefox MV3 uses background.scripts instead of service_worker (for older FF)
      // Firefox 121+ supports service_worker, but for broader compat:
      manifest.browser_specific_settings = {
        gecko: {
          id: 'findablex@findablex.com',
          strict_min_version: '109.0',
        },
      };
      // Firefox 121+ supports service_worker in MV3, keep it
      // For Firefox < 121, would need background.scripts fallback
    }

    if (targetBrowser === 'edge') {
      // Edge is Chromium-based, no changes needed
    }

    return JSON.stringify(manifest, null, 2);
  };

  return {
    entry: {
      'background/service-worker': './src/background/service-worker.ts',
      'popup/popup': './src/popup/popup.ts',
      'content-scripts/injector': './src/content-scripts/injector.ts',
      'content-scripts/engines/deepseek': './src/content-scripts/engines/deepseek.ts',
      'content-scripts/engines/kimi': './src/content-scripts/engines/kimi.ts',
      'content-scripts/engines/qwen': './src/content-scripts/engines/qwen.ts',
      'content-scripts/engines/chatgpt': './src/content-scripts/engines/chatgpt.ts',
      'content-scripts/engines/perplexity': './src/content-scripts/engines/perplexity.ts',
      'content-scripts/engines/doubao': './src/content-scripts/engines/doubao.ts',
      'content-scripts/engines/chatglm': './src/content-scripts/engines/chatglm.ts',
      'content-scripts/engines/google-sge': './src/content-scripts/engines/google-sge.ts',
      'content-scripts/engines/bing-copilot': './src/content-scripts/engines/bing-copilot.ts',
    },
    output: {
      path: outputDir,
      filename: '[name].js',
      clean: true,
    },
    module: {
      rules: [
        {
          test: /\.ts$/,
          use: 'ts-loader',
          exclude: /node_modules/,
        },
        {
          test: /\.css$/,
          use: [MiniCssExtractPlugin.loader, 'css-loader'],
        },
      ],
    },
    resolve: {
      extensions: ['.ts', '.js'],
      alias: {
        '@': path.resolve(__dirname, 'src'),
      },
    },
    plugins: [
      new webpack.DefinePlugin({
        'process.env.TARGET_BROWSER': JSON.stringify(targetBrowser),
      }),
      new MiniCssExtractPlugin({
        filename: '[name].css',
      }),
      new CopyWebpackPlugin({
        patterns: [
          {
            from: 'manifest.json',
            to: 'manifest.json',
            transform: process.env.BROWSER ? manifestTransform : undefined,
          },
          { from: 'src/popup/popup.html', to: 'popup/popup.html' },
          { from: 'src/icons', to: 'icons', noErrorOnMissing: true },
        ],
      }),
    ],
    devtool: isProduction ? false : 'cheap-module-source-map',
    optimization: {
      minimize: isProduction,
    },
  };
};
