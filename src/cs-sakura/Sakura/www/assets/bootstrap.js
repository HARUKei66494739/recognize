// @ts-check
/**
 * @typedef WebConfig
 * @property {number} max_transcript_items
 * @property {number} remove_caption_duration
 * @property {number} websocket_port
 * 
 * @typedef RuleItem
 * @property {string} method
 * @property {string} target
 * @property {string} appearance
 */

function toElement(commnet, rule) {
    console.log(commnet);
    console.log(commnet.transcript);
    console.log(commnet["transcript"]);
    const itemRoot = document.createElement("div");
    itemRoot.classList.add("item");

    const transcribe = document.createElement("div");
    transcribe.classList.add("transcript");

    let input = commnet.transcript;
    let pocd = "";
    root: while (0 < input.length) {
        for (const r of rule) {
            if (input.startsWith(r.target)) {
                const span1 = document.createElement("span");
                span1.innerText = pocd;
                pocd = "";

                const span2 = document.createElement("span");
                span2.classList.add("appearance");
                span2.classList.add(r.appearance);
                span2.innerText = r.target;
                input = input.substring(r.target.length);

                transcribe.appendChild(span1);
                transcribe.appendChild(span2);
                continue root;
            }
        }
        pocd += input[0];
        input = input.substring(1);
    }

    if (pocd.length) {
        const span1 = document.createElement("span");
        span1.innerText = pocd;
        transcribe.appendChild(span1);
    }

    itemRoot.appendChild(transcribe);
    return itemRoot;
}

function updateComment(container, comments, rule) {
    while(container.firstChild) {
        container.removeChild(container.firstChild);
    }
    for(const it of comments) {
        container.appendChild(toElement(it, rule));
    }
}


const MaxInterval = 3000;
let reconnectInterval = 1000;
let socket = null;

class Reconnecter {
    #MaxInterval = 3000;
    #reconnectInterval = 0;
    #timerId = null;

    action = () => { };

    start() {
        if (this.#timerId) {
            clearInterval(this.#timerId);
            this.#timerId = null;
        }
        console.log("start");

        this.#reconnectInterval = 1000;
        this.#timerId = setTimeout(() => {
            console.log("rec");
            this.action();
            reconnectInterval = Math.min(reconnectInterval * 1.5, MaxInterval);
        }, reconnectInterval);
    }

    stop() {
        console.log("stop");

        clearInterval(this.#timerId);
        this.#timerId = null;
    }
}

class Sakura {
    #wsReconnector = new Reconnecter();
    #comments = [];
    /** @type { WebConfig } */
    #webConfig = {}
    /** @type { RuleItem[] } */
    #rule = [];
    #container = null;
    #root = null;

    constructor() {
        this.#root = document.getElementById("sakura-root");
        this.#root.dataset.connected = "0";
        this.#container = document.getElementById("sakura-contents");

        this.#wsReconnector.action = () => this._connect();
    }

    async start() {
        async function get(url) {
            const resp = await fetch(url);
            if (!resp.ok) {
                return null;
            }
            return await resp.json();
        }
        this.#webConfig = await get("/assets/webconfig.json") ?? {};
        this.#rule = await get("/assets/rule.json") ?? [];

        this._connect();
    }



    _connect() {
        try {
            const socket = new WebSocket(`ws://127.0.0.1:${this.#webConfig.websocket_port}`);
            socket.onopen = (e) => {
                this.#root.dataset.connected = "1";
                this.#wsReconnector.stop();
            };
            socket.onclose = () => {
                this.#wsReconnector.start();
                this.#root.dataset.connected = "0";
            };
            socket.onerror = (error) => {
                this.#wsReconnector.start();
                console.log(error);
                this.#root.dataset.connected = "0";
                socket.close();
            };
            socket.onmessage = (e) => {
                const MAX_TRANSCRIBE = this.#webConfig.max_transcript_items;

                this.#comments.push(JSON.parse(e.data));
                if (MAX_TRANSCRIBE < this.#comments.length) {
                    this.#comments.splice(0, this.#comments.length - MAX_TRANSCRIBE);
                }
                updateComment(this.#container, this.#comments, this.#rule);
            };
        }
        catch (e) {
            console.log(e);
        }
    }
}



(async () => {
    new Sakura().start();
})();
