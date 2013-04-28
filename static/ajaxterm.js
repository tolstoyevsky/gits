var Po = Po || {};

Po.namespace = function(ns_string) {
    var parent = Po
      , parts = ns_string.split('.')
      , i = 0;

    if (parts[0] === 'Po')
        parts = parts.slice(1);

    for (; i < parts.length; i++) {
        if (typeof parent[parts[i]] === 'undefined')
            parent[parts[i]] = {};

        parent = parent[parts[i]];
    }

    return parent;
};

(function(exports) {
    'use strict';

    exports.Events = function() {
        this.bind = function(ev, cb) {
            var callbacks = (this.callbacks || (this.callbacks = {}));
            (callbacks[ev] || (callbacks[ev] = [])).push(cb);
        };

        this.trigger = function(ev) {
            var args = [].slice.call(arguments)
              , callbacks = (this.callbacks || (this.callbacks = {}))
              , i = 0;

            if (typeof callbacks[ev] === 'undefined')
                return this;

            for (; i < callbacks[ev].length; i++)
                callbacks[ev][i].apply(this, args.slice(1));
        };
    }

    exports.Screen = function($basis) {
        var _fullscreen_mode = false
          , _fullscreenchange
          , _style;

        this.$node = document.createElement('div');
        this.$node.setAttribute('class', 'terminal-screen');
        this.$node.setAttribute('tabindex', 0);

        if ($basis.firstChild)
            $basis.insertBefore(this.$node, $basis.firstChild);
        else
            $basis.appendChild(this.$node);

        _style = getComputedStyle(this.$node);

        _fullscreenchange = (function(e) {
            if (_fullscreen_mode) {
                _fullscreen_mode = false;
                this.trigger('onexitfullscreen');
            } else
                if ((document.fullscreenElement == this.$node ||
                     document.mozFullScreenElement == this.$node ||
                     document.webkitFullscreenElement == this.$node))
                {
                    _fullscreen_mode = true;
                    this.trigger('onenterfullscreen');
                }
        }).bind(this);

        this.$node.addEventListener('focus', function() {
            document.addEventListener('fullscreenchange',
                                      _fullscreenchange);
            document.addEventListener('mozfullscreenchange',
                                      _fullscreenchange);
            document.addEventListener('webkitfullscreenchange',
                                      _fullscreenchange);
        }, true);

        this.$node.addEventListener('blur', function() {
            document.removeEventListener('fullscreenchange',
                                         _fullscreenchange);
            document.removeEventListener('mozfullscreenchange',
                                         _fullscreenchange);
            document.removeEventListener('webkitfullscreenchange',
                                         _fullscreenchange);
        }, true);

        this.focus = function() {
            this.$node.focus();
        };

        this.getIndent = function() {
            var indent = _style.getPropertyValue('padding-left');

            /*
             * В каких бы допустимых для CSS единицах не было задано значение
             * padding-left, метотод getPropertyValue вернет его в пикселях,
             * поэтому остается только избавиться от префикса px и привести его
             * к целому.
             */
            return parseInt(indent, 10);
        };

        this.setSize = function(width, height) {
            this.$node.style.width = width + 'px';
            this.$node.style.height = height + 'px';
        };
    };

    exports.Screen.prototype = new exports.Events();

    exports.Display = function($screen, row, col) {
        var _style

          , _row = row
          , _col = col

        this.$node = document.createElement('pre')
        this.$node.setAttribute('class', 'terminal-display');

        $screen.appendChild(this.$node);

        _style = getComputedStyle(this.$node);

        WebFont.load({
            active: (function() {
                /*
                 * Дисплей можно считать готовым только после загрузки
                 * перечисленных ниже шрифтов.
                 */
                this.trigger('onready');
            }).bind(this),
            custom: {
                families: ['Droid Sans Mono', 'Ubuntu Mono'],
                urls: ['static/fonts.css']
            }
        });

        function _get_cell_size(font_family, font_size)
        {
            var el = document.createElement('span')
              , rect
              , size = {};

            el.style.fontFamily = font_family;
            el.style.fontSize = font_size;
            el.style.visibility = 'hidden';

            el.appendChild(document.createTextNode('A'));
            document.body.appendChild(el);

            rect = el.getBoundingClientRect();
            size = {
                'width': rect.width,
                'height': rect.height
            };
            document.body.removeChild(el);

            return size;
        };

        this.getCellSize = function() {
            var cache = this.getCellSize.cache
              , font_family = _style.getPropertyValue('font-family')
              , font_size = _style.getPropertyValue('font-size');

            if (cache[font_family] && cache[font_family][font_size])
                return cache[font_family][font_size];

            cache[font_family] = cache[font_family] || {};
            cache[font_family][font_size] = _get_cell_size(font_family,
                                                           font_size);

            return cache[font_family][font_size];
        };

        this.getCellSize.cache = {};

        this.getCol = function() {
            return _col;
        };

        this.getFontSize = function() {
            return _style.getPropertyValue('font-size');
        };

        this.getFontFamily = function() {
            return _style.getPropertyValue('font-family');
        };

        this.getRow = function() {
            return _row;
        };

        this.setResolution = function(row, col) {
            /*
             * Этот метод едва ли перегружен работой (все, что он делает, – это
             * сохраняет количество строк и количество столбцов для последующего
             * использования), но это не должно сбивать с толку. Хотя текущая
             * реализация дисплея могла бы легко обойтись без этого метода,
             * интерфейс разрабатывался с оглядкой на будущее.
             */
            _row = row;
            _col = col;

            /*
             * Изменение разрешения дисплея требует участия как клиента, так и
             * сервера. Однако компонент display не знает и не должен знать о
             * том, как взаимодействовать с сервером. Таким образом, обработчик
             * события onsetresolution предназначен для расширение данного
             * метода.
             */
            this.trigger('onsetresolution', {'row': row, 'col': col});
        };
    };

    exports.Display.prototype = new exports.Events();

    exports.Input = function($screen) {
        var _esc = String.fromCharCode(27)
          , _key_map = { 50: {5: String.fromCharCode(0)},   /* Ctrl-@    */
                        219: {2: String.fromCharCode(27)},  /* Ctrl-[    */
                        220: {2: String.fromCharCode(28)},  /* Ctrl-\    */
                        221: {2: String.fromCharCode(29)},  /* Ctrl-]    */
                         54: {5: String.fromCharCode(30)},  /* Ctrl-^    */
                        173: {5: String.fromCharCode(31)},  /* Ctrl-_    */

                          9: {0: String.fromCharCode(9)},   /* Tab       */
                          8: {0: String.fromCharCode(127)}, /* Backspace */
                         27: {0: _esc},                     /* Escape    */

                         36: {0: _esc + '[1~' }, /* Home  */
                         45: {0: _esc + '[2~' }, /* Ins   */
                         46: {0: _esc + '[3~' }, /* Del   */
                         35: {0: _esc + '[4~' }, /* End   */
                         33: {0: _esc + '[5~' }, /* PgUp  */
                         34: {0: _esc + '[6~' }, /* PgDn  */
                         38: {0: _esc + '[A'  }, /* Up    */
                         40: {0: _esc + '[B'  }, /* Down  */
                         39: {0: _esc + '[C'  }, /* Right */
                         37: {0: _esc + '[D'  }, /* Left  */
                        112: {0: _esc + '[[A' }, /* F1    */
                        113: {0: _esc + '[[B' }, /* F2    */
                        114: {0: _esc + '[[C' }, /* F3    */
                        115: {0: _esc + '[[D' }, /* F4    */
                        116: {0: _esc + '[[E' }, /* F5    */
                        117: {0: _esc + '[17~'}, /* F6    */
                        118: {0: _esc + '[18~'}, /* F7    */
                        119: {0: _esc + '[19~'}, /* F8    */
                        120: {0: _esc + '[20~'}, /* F9    */
                        121: {0: _esc + '[21~'}, /* F10   */
                        122: {0: _esc + '[23~'}, /* F11   */
                        123: {0: _esc + '[24~'}  /* F12   */ }
          , _keydown
          , _keypress;

        _keydown = (function(e) {
            var aflg = (e.altKey)   ? 4 /* 100b */ : 0
              , cflg = (e.ctrlKey)  ? 2 /* 010b */ : 0
              , sflg = (e.shiftKey) ? 1 /* 001b */ : 0
              , sum  = aflg | cflg | sflg

              , k = '';

            /* TODO: добавить обработчики Ctrl-Alt-A..Z и Alt-A..Z. */

            if (cflg && e.keyCode >= 65 /* A */ && e.keyCode <= 90 /* Z */)
                /*
                 * По номеру символа A..Z можно получить номер управляющего
                 * символа, представленного комбинацией клавиш Ctrl-A..Z.
                 */
                k = String.fromCharCode(e.keyCode - 64); // Ctrl-A..Z
            else
                k = (e.keyCode in _key_map) ? _key_map[e.keyCode][sum] : '';

            if (k) {
                this.trigger('oninput', k);
                e.preventDefault();
            }
        }).bind(this);

        _keypress = (function(e) {
            /*
             * В Chrome и Firefox событие keypress возникает при нажатии на
             * клавишу Enter несмотря на то, что она представляет непечатаемый
             * символ. При этом в Chrome свойство e.charCode получает значение
             * 13, а в Firefox – 0. Необходимо приблизить поведение Firefox к
             * Chrome и другим браузерам.
             */
            var char_code = (e.keyCode == 13) ? 13 : e.charCode
              , k = '';

            /*
             * В Firefox, в отличии от Chrome и других браузеров, событие
             * keypress возникает при нажатии клавиш, представляющих
             * непечатаемые символы. Таким образом, их необходимо игнорировать,
             * т. к. обработкой комбинаций клавиш и непечатаемых символов
             * занимается keydown.
             */
            if (!e.altKey && !e.ctrlKey && char_code) {
                k = String.fromCharCode(char_code);
                this.trigger('oninput', k);
            }
        }).bind(this);

        $screen.addEventListener('focus', function() {
            document.addEventListener('keydown',  _keydown);
            document.addEventListener('keypress', _keypress);
        }, true);

        $screen.addEventListener('blur', function() {
            document.removeEventListener('keydown',  _keydown);
            document.removeEventListener('keypress', _keypress);
        }, true);
    };

    exports.Input.prototype = new exports.Events();
}(Po.namespace('Po.primitives')));

(function(exports) {
    exports.Terminal = function($basis, row, col) {
        var _row = (typeof row === 'undefined') ? 24 : row
          , _col = (typeof col === 'undefined') ? 80 : col

          , _fit_screen_size
          , _input
          , _ws;

        _fit_screen_size = (function(row, col) {
            var cell = this.display.getCellSize()
              , width = col * cell.width
              , height = row * cell.height;

            this.screen.setSize(width, height);
        }).bind(this);

        this.screen = new Po.primitives.Screen($basis);
        this.display = new Po.primitives.Display(this.screen.$node, _row, _col);

        /*
         * Подогнать размер экрана под разрешение дисплея, переданное в качестве
         * параметров.
         */
        this.display.bind('onready', function() {
            _fit_screen_size(_row, _col);
        });

        _input = new Po.primitives.Input(this.screen.$node);
        _ws = new WebSocket('ws://' + location.host + '/termsocket');

        /*
         * При переходе экрана в полноэкранный режим, необходимо рассчитать
         * оптимальное разрешение дисплея.
         */
        this.screen.bind('onenterfullscreen', (function() {
            var cell = this.display.getCellSize()
              , indent = this.screen.getIndent()
              , row = (window.screen.height - indent * 2) / cell.height
              , col = (window.screen.width - indent * 2) / cell.width;

            _row = this.display.getRow();
            _col = this.display.getCol();
            this.display.setResolution(Math.floor(row), Math.floor(col));
        }).bind(this));

        this.screen.bind('onexitfullscreen', (function() {
            this.display.setResolution(_row, _col);
        }).bind(this));

        this.display.bind('onsetresolution', function(e) {
            _fit_screen_size(e.row, e.col);
            _ws.send('rsz,' + e.row + 'x' + e.col);
        });

        _input.bind('oninput', function(data) {
            _ws.send('key,' + data);
        });

        _ws.onmessage = (function(e) {
            this.display.$node.innerHTML = e.data;
        }).bind(this);
    };
}(Po.namespace('Po')));
