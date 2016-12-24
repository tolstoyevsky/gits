export class Events {
    constructor() {
        this.callbacks = {};
    }

    bind(ev, cb) {
        const callbacks = this.callbacks;
        (callbacks[ev] || (callbacks[ev] = [])).push(cb);
    }

    trigger(ev) {
        var args = [].slice.call(arguments)
          , callbacks = (this.callbacks || (this.callbacks = {}))
          , i = 0;

        if (typeof callbacks[ev] === 'undefined')
            return this;

        for (; i < callbacks[ev].length; i++)
            callbacks[ev][i].apply(this, args.slice(1));
    };
}
