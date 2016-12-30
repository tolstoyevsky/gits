import { Events } from './events';

export class Input extends Events {
    constructor($screen) {
        super();

        const _esc = String.fromCharCode(27);
        const _key_map = { 50: {5: String.fromCharCode(0)}, /* Ctrl-@    */
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
                        123: {0: _esc + '[24~'}  /* F12   */ };

        const _keydown = e => {
            const aflg = (e.altKey)   ? 4 /* 100b */ : 0;
            const cflg = (e.ctrlKey)  ? 2 /* 010b */ : 0;
            const sflg = (e.shiftKey) ? 1 /* 001b */ : 0;
            const sum  = aflg | cflg | sflg;
            let k = '';

            /* TODO: handle Ctrl-Alt-A..Z and Alt-A..Z. */

            if (cflg && e.keyCode >= 65 /* A */ && e.keyCode <= 90 /* Z */) {
                /*
                 * Using ASCII numeric representations of the letters A-Z,
                 * figure out ASCII numeric representations of the control
                 * characters Ctrl-A..Z
                 */
                k = String.fromCharCode(e.keyCode - 64); // Ctrl-A..Z
            } else {
                k = (e.keyCode in _key_map) ? _key_map[e.keyCode][sum] : '';
            }

            if (k) {
                this.trigger('oninput', k);
                e.preventDefault();
            }
        };

        const _keypress = e => {
            /*
             * Chrome and Firefox fire the keypress event when the user presses
             * the Enter key in spite of the fact it represents a non-printable
             * character. Furthermore, in Chrome e.charCode gets 13 when in
             * Firefox e.charCode gets 0. Make Firefox behave like
             * Chrome and other browsers.
             */
            const char_code = (e.keyCode == 13) ? 13 : e.charCode;

            /*
             * Firefox fires the keypress event when the user presses
             * non-printable characters. Ignore the characters since keydown
             * handles them.
             */
            if (!e.altKey && !e.ctrlKey && char_code) {
                let k = String.fromCharCode(char_code);
                this.trigger('oninput', k);
            }
        };

        $screen.addEventListener('focus', () => {
            document.addEventListener('keydown',  _keydown);
            document.addEventListener('keypress', _keypress);
        }, true);

        $screen.addEventListener('blur', () => {
            document.removeEventListener('keydown',  _keydown);
            document.removeEventListener('keypress', _keypress);
        }, true);
    }
};
