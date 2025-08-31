const path = require('path');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const CssMinimizerPlugin = require('css-minimizer-webpack-plugin');
const CopyPlugin = require('copy-webpack-plugin');

module.exports = (env, argv) => {
  const isProduction = argv.mode === 'production';

  return {
    entry: {
      // Main app bundle
      app: './app/static/js/app.js',
      // Vendor bundle (Bootstrap, jQuery, Font Awesome)
      vendor: './app/static/js/vendor.js'
    },
    output: {
      filename: 'js/[name].bundle.js',
      path: path.resolve(__dirname, 'app/static/dist'),
      clean: true
    },
    module: {
      rules: [
        {
          test: /\.js$/,
          exclude: /node_modules/,
          use: {
            loader: 'babel-loader',
            options: {
              presets: ['@babel/preset-env']
            }
          }
        },
        {
          test: /\.(scss|sass|css)$/,
          use: [
            isProduction ? MiniCssExtractPlugin.loader : 'style-loader',
            'css-loader',
            'sass-loader'
          ]
        },
        {
          test: /\.(woff|woff2|eot|ttf|otf)$/,
          type: 'asset/resource',
          generator: {
            filename: 'fonts/[name][ext]'
          }
        },
        {
          test: /\.(png|svg|jpg|jpeg|gif)$/,
          type: 'asset/resource',
          generator: {
            filename: 'images/[name][ext]'
          }
        }
      ]
    },
    plugins: [
      new MiniCssExtractPlugin({
        filename: 'css/[name].bundle.css'
      }),
      new CopyPlugin({
        patterns: [
          // Copy Font Awesome webfonts
          {
            from: 'node_modules/@fortawesome/fontawesome-free/webfonts',
            to: 'webfonts'
          }
        ]
      })
    ],
    optimization: {
      minimizer: [
        `...`, // Keep default minimizers
        new CssMinimizerPlugin()
      ]
    },
    devtool: isProduction ? false : 'source-map'
  };
};