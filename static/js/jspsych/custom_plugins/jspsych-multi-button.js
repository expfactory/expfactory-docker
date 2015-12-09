/**
 * jspsych-multi-button
 * Ian Eisenberg
 *
 * plugin for displaying buttons and getting mouse responses
 *
 * documentation: docs.jspsych.org
 *
 **/
 
jsPsych['multi-button'] = (function(){

    var plugin = {};

    plugin.create = function(params){
        var trials = new Array(params.buttons.length);
			for (var i = 0; i < trials.length; i++) {
				trials[i] = {};
				trials[i].buttons = params.buttons[i];
				trials[i].button_class = params.button_class;
				trials[i].response_ends_trial = (typeof params.response_ends_trial === 'undefined') ? true : params.response_ends_trial;
				// timing parameters
				trials[i].timing_stim = params.timing_stim || -1; // if -1, then show indefinitely
				trials[i].timing_response = params.timing_response || -1; // if -1, then wait for response forever
				// optional parameters
				trials[i].prompt = (typeof params.prompt === 'undefined') ? "" : params.prompt;
			}
			return trials;
    }
    
    

    plugin.trial = function(display_element, trial){
		
		var start_time = (new Date()).getTime();
		var response = {rt: -1, mouse: -1};
		
		// this array holds handlers from setTimeout calls
		// that need to be cleared if the trial ends early
		var setTimeoutHandlers = [];
		
		// function to end trial when it is time
		var end_trial = function() {

			// kill any remaining setTimeout handlers
			for (var i = 0; i < setTimeoutHandlers.length; i++) {
				clearTimeout(setTimeoutHandlers[i]);
			}

			// gather the data to store for the trial
			var trial_data = {
				"rt": response.rt,
				"mouse_click": response.mouse
			};

			jsPsych.data.write(trial_data);

			// clear the display
			display_element.html('');

			// move on to the next trial
			jsPsych.finishTrial();
		};		
		
		// display stimulus
		display_element.append($('<div>', {
					html: trial.buttons,
					id: 'jspsych-multi-button-stimulus'
				}));
				
		//show prompt if there is one
			if (trial.prompt !== "") {
				display_element.append(trial.prompt);
			}
		
		//Define button press behavior
        $('.' + trial.button_class).on('click',function(){
			if(response.mouse == -1){
				var end_time = (new Date()).getTime();
				var rt = end_time - start_time;
				var originalColor = $(this).css('color')
				
				response.rt = rt
				response.mouse = $(this).text()
				$(this).addClass('responded')
				if (trial.response_ends_trial) {
					end_trial();
				}
			}
        });
		
		// hide image if timing is set
		if (trial.timing_stim > 0) {
			var t1 = setTimeout(function() {
				$('#jspsych-multi-stim-stimulus').css('visibility', 'hidden');
			}, trial.timing_stim);
			setTimeoutHandlers.push(t1);
		}

		// end trial if time limit is set
		if (trial.timing_response > 0) {
			var t2 = setTimeout(function() {
				end_trial();
			}, trial.timing_response);
			setTimeoutHandlers.push(t2);
		}
    }

    return plugin;

})();