import { Events } from './events';

export class Display extends Events {
    constructor($screen, row, col) {
        super();

        this._row = row;
        this._col = col;
        this.cellSizeCache = {};

        this.$node = document.createElement('pre')
        this.$node.setAttribute('class', 'terminal-display');

        $screen.appendChild(this.$node);

        this._style = getComputedStyle(this.$node);
    }

    _get_cell_size(font_family, font_size) {
        const $el = document.createElement('span');

        $el.style.fontFamily = font_family;
        $el.style.fontSize = font_size;
        $el.style.visibility = 'hidden';

        $el.appendChild(document.createTextNode('A'));
        document.body.appendChild($el);

        const rect = $el.getBoundingClientRect();
        const size = {
            'width': rect.width,
            'height': rect.height
        };
        document.body.removeChild($el);

        return size;
    }

    getCellSize() {
        const cache = this.cellSizeCache;
        const font_family = this._style.getPropertyValue('font-family')
        const font_size = this._style.getPropertyValue('font-size');

        if (cache[font_family] && cache[font_family][font_size])
            return cache[font_family][font_size];

        cache[font_family] = cache[font_family] || {};
        cache[font_family][font_size] = this._get_cell_size(font_family,
                                                       font_size);

        return cache[font_family][font_size];
    }

    getCol() {
        return this._col;
    }

    getFontSize() {
        return this._style.getPropertyValue('font-size');
    }

    getFontFamily() {
        return this._style.getPropertyValue('font-family');
    }

    getRow() {
        return this._row;
    }

    setResolution(row, col) {
        this._row = row;
        this._col = col;

        /*
         * Changing display resolution requires involvement of both the server
         * and the client. However, the display component doesn't know how to
         * interact with the server. Thus, the onsetresolution event handler is
         * intended for expanding the method.
         */
        this.trigger('onsetresolution', {'row': row, 'col': col});
    }
};
