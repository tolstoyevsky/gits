const path = require('path');
const webpack = require('webpack');
const appModulesRoot = path.resolve(__dirname, 'static');
const nodeModulesRoot = path.resolve(__dirname, 'node_modules');

const config = {
    entry: {
        'main': './static/basic/index',
        'control-panel': './static/control-panel/index',
    },

    output: {
        path: path.resolve(__dirname, 'static', 'bundles'),
        filename: '[name].js'
    },

    module: {
        rules: [
            {
                test: /\.js$/,
                use: [
                    {
                        loader: 'babel-loader',
                        options: {
                            presets: ['es2015'],
                        },
                    }
                ],
            },
            {
                test: /\.less$/,
                use: [
                    'style-loader',
                    {
                        loader: 'css-loader',
                        options: {
                            importLoaders: 1,
                        },
                    },
                    'less-loader',
                ],
            },
            {
                // fonts
                test: /\.(eot|woff|woff2|ttf|png|jpg)$/,
                use: ['url-loader'],
            },
            {
                test: /\.svg$/,
                use: ['tv-webpack-svg-loader'],
            }
        ]
    },

    resolve: {
        modules: [appModulesRoot, nodeModulesRoot],
        extensions: ['.js'],
    },

    plugins: [],
};

if (process.env.NODE_ENV === 'production') {
    config.plugins.push(
        new webpack.optimize.UglifyJsPlugin({
            minimize: true,
            sourceMap: false,
            output: {
                comments: false
            },
            compress: {
                warnings: false,
                drop_console: true,
                unsafe: true,
                dead_code: true,
                drop_debugger: true,
                conditionals: true,
                loops: true,
                unused: true,
                hoist_funs: true,
                hoist_vars: true,
                if_return: true,
                join_vars: true,
            },
        })
    );
} else {
    config.devtool = "#source-map";
}

module.exports = config;
