document.addEventListener('DOMContentLoaded', function() {
    var $basis = document.getElementById('control-panel')
      , btn = document.querySelector('.full-screen button')
      , terminal = new Po.Terminal($basis);

    terminal.screen.focus();

    btn.onclick = function() {
        var screen = terminal.screen.$node;

        if (!screen.requestFullscreen)
            screen.requestFullscreen = screen.requestFullscreen ||
                                       screen.mozRequestFullScreen ||
                                       screen.webkitRequestFullscreen;

        screen.requestFullscreen();
        terminal.screen.focus();
    };
});
