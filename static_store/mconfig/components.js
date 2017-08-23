Vue.component('mconfig-hint', {
	props: ['mHint'],
	template: '<div class="help"> \
					<i class="icon-help">?</i> \
					<div class="help-popup"> \
						<i class="help-popup-ctrl" ></i> \
							{{mHint}} \
					</div> \
				</div>'
});

Vue.component('mconfig-edit', {
	props: ['mName', 'mEnabled', 'mHint', 'mValue', 'mError'],
	template: '<div class="choice-field"> \
					<label>{{ mName }}</label> \
					<input \
						v-model="mValue"\
						class="w3-input" \
						type="text"\
						:value="mValue"\
						v-on:change="post(false)" \
						v-on:input="post(true)"\
					>\
					</input> \
					<mconfig-hint :m-hint="mHint"></mconfig-hint>\
					<label class="error-hint"> {{mError}} </label> \
			</div>',
	methods: {
		post: function (soft) {
			postFieldValue(this, soft);
		},
		update: function (data) {
			this.mValue = data.value;
		}
	}
});

Vue.component('mconfig-choice', {
	props: ['mName', 'mChoices', 'mEnabled', 'mHint', 'mValue', 'mError'],
	template: '<div class="choice-field">\
	<label :for="mName">{{mName}}</label>\
	<select\
		:name="mName"\
		:id="mName"	\
		class="question" \
		v-on:change="post(true)">\
		<option v-for="choice in mChoices"\
			:id="mName+\'_\'+choice"\
			:value="choice"\
			:disabled="!mEnabled"\
			:selected="choice == mValue"\
			>\
				{{choice}}\
		</option>\
	</select>\
	<mconfig-hint :m-hint="mHint"></mconfig-hint>\
	<label class="error-hint"> {{mError}} </label> \
	</div>',
	methods: {
		post: function (me, soft) {
			postFieldValue(me, soft);
		},
		update: function (data) {
			
		}
	}	
});

Vue.component('mconfig-searchchoice', {
	props: ['mName', 'mChoices', 'mEnabled', 'mHint', 'mValue', 'mError'],
	template: '<div class="">\
	<strong>{{mName}}</strong><br/>\
	<select :name="mName"\
			:id="mName"\
			class="sel-apl"\
			autocomplete="off"\
			:disabled="!mEnabled"\
			:value="mValue"\
            v-on:change="post(true)">\
		<option v-for="choice in mChoices"\
			:id="mName+\'_\'+choice"\
			:value="choice"\
			:disabled="!mEnabled"\
			:selected="choice == mValue"\
			>\
				{{choice}}\
		</option>\
	</select>\
	<mconfig-hint :m-hint="mHint"></mconfig-hint>\
	</div>',
	methods: {
		post: function (me, soft) {
			postFieldValue(me, soft);
		},
		update: function (data) {
			
		}
	}
});