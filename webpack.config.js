const path = require('path');
const appModulesRoot = path.resolve(__dirname, 'static');
const nodeModulesRoot = path.resolve(__dirname, 'node_modules');

module.exports = {
    entry: {
        main: './static/index',
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
                test: /\.(eot|woff|woff2|ttf|svg|png|jpg)$/,
                use: [
                    'url-loader?name=[name]-[hash].[ext]'
                ],
            },
        ]
    },

    resolve: {
        modules: [appModulesRoot, nodeModulesRoot],
        extensions: ['.js'],
    },

    devtool: 'source-map',
};
