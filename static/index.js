import './fonts.less';

import { Terminal } from 'terminal';

document.addEventListener('DOMContentLoaded', function() {
    const $basis = document.getElementById('basic');
    const terminal = new Terminal($basis);

    terminal.screen.focus();
});
