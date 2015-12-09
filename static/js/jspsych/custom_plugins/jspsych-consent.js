/*
jspsych-consent

a jspsych plugin to create a consent page and check for response without requring an external html page

Ayse Zeynep Enkavi*/

//Look at text plugin for text and likert scale plugin for button

// parameters:
// consent_text
// checkbox_text
// button_text

(function($) {
  jsPsych['consent'] = (function(){

    var plugin = {};

    plugin.create = function(params){

      params = jsPsych.pluginAPI.enforceArray(params, ['consent_text', 'checkbox_text', 'button_text']);
      
      var trials = new Array(params.consent_text.length);

      for(var i = 0; i<trials.length; i++){
        trials[i] = {};
        trials[i].consent_text = params.consent_text[i];
        trials[i].checkbox_text = params.checkbox_text[i];
        trials[i].button_text = params.button_text[i];
        trials[i].container = params.container || -1
      }

      return trials;
    }

    plugin.trial = function(display_element, trial){

      trial = jsPsych.pluginAPI.evaluateFunctionParameters(trial);

      //display consent text, checkbox and button
      display_element.append($('<div>', {
					html: trial.consent_text + //consent_text - should specify a container
						"<p class = block-text><input type='checkbox' id = 'checkbox'>" + trial.checkbox_text + "</p>" +
						"<button type='button' id = 'start'>" + trial.button_text +"</button>",
					id: 'jspsych-consent-text'
				}));


      //specify what happens when start button is clicked
      $("#start").click(function() {
        
        // measure response time
        var endTime = (new Date()).getTime();
        var response_time = endTime - startTime;

        // check if consent given
        if ($('#checkbox').is(':checked')) {
          // save data
          jsPsych.data.write({
            "rt": response_time,
          });

          display_element.html('');

          // next trial
          jsPsych.finishTrial();
          
          //return true;
        }

        // if consent not given alert subject and don't start
        else {
          alert("If you wish to participate, you must check the box to agree to participate in this study.");
          return false;
        }

      });
      
   var startTime = (new Date()).getTime();  
  };

    return plugin;

  })();
})(jQuery);
