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
        /*
         * Этот метод едва ли перегружен работой (все, что он делает, – это
         * сохраняет количество строк и количество столбцов для последующего
         * использования), но это не должно сбивать с толку. Хотя текущая
         * реализация дисплея могла бы легко обойтись без этого метода,
         * интерфейс разрабатывался с оглядкой на будущее.
         */
        this._row = row;
        this._col = col;

        /*
         * Изменение разрешения дисплея требует участия как клиента, так и
         * сервера. Однако компонент display не знает и не должен знать о
         * том, как взаимодействовать с сервером. Таким образом, обработчик
         * события onsetresolution предназначен для расширение данного
         * метода.
         */
        this.trigger('onsetresolution', {'row': row, 'col': col});
    }
};
