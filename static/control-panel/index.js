import 'fonts.less';
import './control-panel.less';

import { controlPanelTmpl } from './template';

import { Terminal } from 'terminal';

document.addEventListener('DOMContentLoaded', function () {
    const $terminal = document.querySelector('.terminal-with-control-panel');
    $terminal.innerHTML = controlPanelTmpl;

    const $btn = $terminal.querySelector('.full-screen button');
    $btn.onclick = function() {
        terminal.screen.requestFullScreen();
        terminal.screen.focus();
    };

    const terminal = new Terminal($terminal);
    terminal.screen.focus();
});
