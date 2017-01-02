import { Events } from './events';

export class Screen extends Events {
    constructor($basis) {
        super();

        let _fullscreen_mode = false;

        this.$node = document.createElement('div');
        this.$node.setAttribute('class', 'terminal-screen');
        this.$node.setAttribute('tabindex', 0);

        if ($basis.firstChild) {
            $basis.insertBefore(this.$node, $basis.firstChild);
        } else {
            $basis.appendChild(this.$node);
        }

        this._style = getComputedStyle(this.$node);

        const _fullscreenchange = e => {
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
        };

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
    }

    focus() {
        this.$node.focus();
    }

    getIndent() {
        const indent = this._style.getPropertyValue('padding-left');

        return parseInt(indent, 10);
    }

    setSize(width, height) {
        this.$node.style.width = width + 'px';
        this.$node.style.height = height + 'px';
    }

    requestFullScreen() {
        return ($node => {
            return (
                $node.requestFullscreen ||
                $node.webkitRequestFullscreen ||
                $node.mozRequestFullScreen ||
                function() {
                    console.warn(
                        'browser does not support requestFullscreen API'
                    );
                }
            ).call($node);
        })(this.$node);
    }
};
