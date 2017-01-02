import 'fonts.less';

import { Terminal } from 'terminal';

document.addEventListener('DOMContentLoaded', function () {
    const $terminal = document.querySelector('.terminal');
    const terminal = new Terminal($terminal);

    terminal.screen.focus();
});
