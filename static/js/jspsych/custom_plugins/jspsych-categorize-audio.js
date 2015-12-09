/**
 * jspsych-categorize-audio
 * Ian Eisenberg
 *
 * plugin for playing an audio file, getting a keyboard response, and giving feedback
 *
 * 
 *
 **/

(function($) {
	jsPsych["categorize-audio"] = (function() {

		var plugin = {};

		var context = new AudioContext();

		plugin.create = function(params) {

			params = jsPsych.pluginAPI.enforceArray(params, ['choices', 'key_answer', 'text_answer']);

			var trials = new Array(params.stimuli.length);

			for (var i = 0; i < trials.length; i++) {

				trials[i] = {};
				trials[i].audio_stim = jsPsych.pluginAPI.loadAudioFile(params.stimuli[i]);
				trials[i].audio_path = params.stimuli[i];
				trials[i].choices = params.choices || [];
				// option to show image for fixed time interval, ignoring key responses
				//      true = image will keep displaying after response
				//      false = trial will immediately advance when response is recorded
				trials[i].key_answer = params.key_answer[i];
				trials[i].text_answer = (typeof params.text_answer === 'undefined') ? "" : params.text_answer[i];
				trials[i].correct_text = (typeof params.correct_text === 'undefined') ? "<p class='feedback'>Correct</p>" : params.correct_text;
				trials[i].incorrect_text = (typeof params.incorrect_text === 'undefined') ? "<p class='feedback'>Incorrect</p>" : params.incorrect_text;
				trials[i].response_ends_trial = (typeof params.response_ends_trial === 'undefined') ? true : params.response_ends_trial;
				trials[i].force_correct_button_press = (typeof params.force_correct_button_press === 'undefined') ? false : params.force_correct_button_press;
				trials[i].prompt = (typeof params.prompt === 'undefined') ? '' : params.prompt;
				trials[i].show_feedback_on_timeout = (typeof params.show_feedback_on_timeout === 'undefined') ? false : params.show_feedback_on_timeout;
				trials[i].timeout_message = params.timeout_message || "<p>Please respond faster.</p>";
				// timing parameters
				// trials[i].timing_stim = params.timing_stim || -1; // if -1, then show indefinitely
				trials[i].timing_response = params.timing_response || -1; // if -1, then wait for response forever
				trials[i].prompt = (typeof params.prompt === 'undefined') ? "" : params.prompt;
				trials[i].timing_feedback_duration = params.timing_feedback_duration || 2000;

			}

			return trials;
		};

		plugin.trial = function(display_element, trial) {

			// if any trial variables are functions
			// this evaluates the function and replaces
			// it with the output of the function
			trial = jsPsych.pluginAPI.evaluateFunctionParameters(trial);

			// this array holds handlers from setTimeout calls
			// that need to be cleared if the trial ends early
			var setTimeoutHandlers = [];

			// play stimulus
			var source = context.createBufferSource();
			source.buffer = jsPsych.pluginAPI.getAudioBuffer(trial.audio_stim);
			source.connect(context.destination);
			startTime = context.currentTime + 0.1;
			source.start(startTime);

			// show prompt if there is one
			if (trial.prompt !== "") {
				display_element.append(trial.prompt);
			}

			// store response
			var response = {rt: -1, key: -1};

			// function to end trial when it is time
			var end_trial = function() {

				// kill any remaining setTimeout handlers
				for (var i = 0; i < setTimeoutHandlers.length; i++) {
					clearTimeout(setTimeoutHandlers[i]);
				}

				


				// move on to the next trial
				jsPsych.finishTrial();
			};

			// function to handle responses by the subject
			var after_response = function(info) {

				// kill any remaining setTimeout handlers
				for (var i = 0; i < setTimeoutHandlers.length; i++) {
					clearTimeout(setTimeoutHandlers[i]);
				}

				// clear keyboard listener
				jsPsych.pluginAPI.cancelAllKeyboardResponses();

				var correct = false;
				if (trial.key_answer == info.key) {
					correct = true;
				}
				console.log(trial.key_answer)
				console.log(info.key)

				// save data
				var trial_data = {
					"rt": info.rt,
					"correct": correct,
					"stimulus": trial.a_path,
					"key_press": info.key
				};

				jsPsych.data.write(trial_data);

				display_element.html('');

				var timeout = info.rt == -1;
				doFeedback(correct, timeout);
			};

			jsPsych.pluginAPI.getKeyboardResponse({
        callback_function: after_response,
        valid_responses: trial.choices,
        rt_method: 'date',
        persist: false,
				allow_held_key: false
      });

			if(trial.timing_response > 0) {
				setTimeoutHandlers.push(setTimeout(function(){
					after_response({key: -1, rt: -1});
				}, trial.timing_response));
			}

			function doFeedback(correct, timeout) {

				if(timeout && !trial.show_feedback_on_timeout){
					display_element.append(trial.timeout_message);
				} else {
					// substitute answer in feedback string.
					var atext = "";
					if (correct) {
						atext = trial.correct_text.replace("%ANS%", trial.text_answer);
					} else {
						atext = trial.incorrect_text.replace("%ANS%", trial.text_answer);
					}

					// show the feedback
					display_element.append(atext);
				}
				// check if force correct button press is set
				if (trial.force_correct_button_press && correct === false && ((timeout && trial.show_feedback_on_timeout) || !timeout)) {

					var after_forced_response = function(info) {
						endTrial();
					}

					jsPsych.pluginAPI.getKeyboardResponse({
		        callback_function: after_forced_response,
		        valid_responses: [trial.key_answer],
		        rt_method: 'date',
		        persist: false,
	          allow_held_key: false
		      });

				} else {
					setTimeout(function() {
						endTrial();
					}, trial.timing_feedback_duration);
				}

			}

			function endTrial() {
				display_element.html("");
				// stop the audio file if it is playing
				source.stop();
				
				jsPsych.finishTrial();
			}

		};

		return plugin;
	})();
})(jQuery);

