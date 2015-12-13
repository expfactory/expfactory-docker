/*
 * Modified from psiturk.js
 * Requires:
 *     jquery
 *     backbone.js
 */


/*******
 * API *
 ******/
var ExpFactory = function(uniqueId) {
    var self = this;
	
	var TaskData = Backbone.Model.extend({
		id: uniqueId,
        urlRoot: "/sync",		

		defaults: {
			condition: 0,
			counterbalance: 0,
			assignmentId: 0,
			workerId: 0,
			hitId: 0,
			currenttrial: 0,
			bonus: 0,
			data: [],
			questiondata: {},
			eventdata: [],
			useragent: ""
		},
		
		initialize: function() {
			this.useragent = navigator.userAgent;
			this.addEvent('initialized', null);
			this.addEvent('window_resize', [window.innerWidth, window.innerHeight]);
		},

		addTrialData: function(trialdata) {
			trialdata = {"uniqueid":this.id, "current_trial":this.get("currenttrial"), "dateTime":(new Date().getTime()), "trialdata":trialdata};
			var data = this.get('data');
			data.push(trialdata);
			this.set('data', data);
			this.set({"currenttrial": this.get("currenttrial")+1});
		},
		
		addUnstructuredData: function(field, response) {
			var qd = this.get("questiondata");
			qd[field] = response;
			this.set("questiondata", qd);
		},
		
		getTrialData: function() {
			return this.get('data');	
		},
		
		getEventData: function() {
			return this.get('eventdata');	
		},
		
		getQuestionData: function() {
			return this.get('questiondata');	
		},
		
		addEvent: function(eventtype, value) {
			var interval,
			    ed = this.get('eventdata'),
			    timestamp = new Date().getTime();

			if (eventtype == 'initialized') {
				interval = 0;
			} else {
				interval = timestamp - ed[ed.length-1]['timestamp'];
			}

			ed.push({'eventtype': eventtype, 'value': value, 'timestamp': timestamp, 'interval': interval});
			this.set('eventdata', ed);
		}
	});
	
	// Add a line of data with any number of columns
	self.recordTrialData = function(trialdata) {
		taskdata.addTrialData(trialdata);
	};
	
	// Add data value for a named column. If a value already
	// exists for that column, it will be overwritten
	self.recordUnstructuredData = function(field, value) {
		taskdata.addUnstructuredData(field, value);
	};

	self.getTrialData = function() {
		return taskdata.getTrialData();	
	};
		
	self.getEventData = function() {
		return taskdata.getEventData();	
	};
		
	self.getQuestionData = function() {
		return taskdata.getQuestionData();	
	};

	// Save data to server
	self.saveData = function(callbacks) {
		taskdata.save(undefined, callbacks);
	};
	
	self.completeHIT = function() {
        console.log("HIT complete.");
		//window.location = self.taskdata.adServerLoc + "?uniqueId=" + self.taskdata.id;
	}

	var taskdata = new TaskData();
	taskdata.fetch({async: false});
	
	/*  DATA: */
	self.pages = {};
	self.taskdata = taskdata;

	return self;
};

// vi: noexpandtab nosmartindent shiftwidth=4 tabstop=4
