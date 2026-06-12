Component({ properties: { comments: { type: Array, value: [] } }, methods: { reply(e) { this.triggerEvent('reply', e.currentTarget.dataset); } } });
