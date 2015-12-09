/**
 * jspsych-radio-buttonlist
 * a jspsych plugin for displaying a form with a list of radio buttons
 *
 * A. Zeynep Enkavi 
 *
 * TO DO:
 * Add different types of buttons (radio, checklist etc.)
 * Add checkAll parameter that would alert if there are blank questions
 */

(function($) {
  jsPsych['radio-buttonlist'] = (function() {

    var plugin = {};

    plugin.create = function(params) {

      //params = jsPsych.pluginAPI.enforceArray(params, ['data']);

      var trials = [];
      for (var i = 0; i < params.buttonlist.length; i++) {
        trials.push({
          preamble: (typeof params.preamble === 'undefined') ? "" : params.preamble[i],
          buttonlist: params.buttonlist[i],
          checkAll: params.checkAll[i],
          numq: params.numq[i]
        });
      }
      return trials;
    };

    plugin.trial = function(display_element, trial) {

      // if any trial variables are functions
      // this evaluates the function and replaces
      // it with the output of the function
      trial = jsPsych.pluginAPI.evaluateFunctionParameters(trial);

      // show preamble text
      display_element.append($('<div>', {
        "id": 'jspsych-radio-buttonlist-preamble',
        "class": 'jspsych-radio-buttonlist-preamble'
      }));

      $('#jspsych-radio-buttonlist-preamble').append(trial.preamble);
      
      //Display form with a specific name (referred to later when submit button is clicked)
      //Appending directly instead of adding a div first and then populating it
      display_element.append('<form id = "jspsych-radio-buttonlist">' + buttonlist + '</form>');

      // helper function to loop through each button in form and submit data
      function loopForm(form, checkAll) {
      // measure response time (to be submitted with data - per page for now)
      var endTime = (new Date()).getTime();
      var response_time = endTime - startTime;
        // count question number for trial_index
      var qnum = 1;

      //alert if all q's on page are mandatory but not answered and stay on page if not
      if (checkAll){
        if($("input[type=radio]:checked").length < trial.numq){
          alert("Please make sure to answer all questions.");
          return;
        }
      }
      
      //loop through all checked radio buttons
      for (var i = 0; i < form.elements.length; i++ ) {
          if (form.elements[i].type == 'radio') {
            if (form.elements[i].checked == true) {
              //write data for each checked radio button
              jsPsych.data.write({
                'rt': response_time,
                'response': (form.elements[i].value)
              });
              //add trial number to data
              jsPsych.data.addDataToLastTrial({trial_index: form.elements[i].name});
              }
            }
          }
        

        display_element.html('');

        // next trial
        jsPsych.finishTrial();
      };      

      // add submit button
      display_element.append($('<button>', {
        'id': 'jspsych-radio-buttonlist-next',
        'class': 'jspsych-radio-buttonlist'
      }));

      //add display text to button
      $("#jspsych-radio-buttonlist-next").html('Submit Answers');
      
      //define on click function for button
      $("#jspsych-radio-buttonlist-next").click(function() {
        
        var thisForm = document.getElementById("jspsych-radio-buttonlist");

        loopForm(thisForm, trial.checkAll);

      });

      var startTime = (new Date()).getTime();
    };

    return plugin;
  })();
})(jQuery);
