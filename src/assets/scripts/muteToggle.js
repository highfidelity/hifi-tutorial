//
// muteToggle.js
// 
// Author: Liv Erickson
// Copyright High Fidelity 2018
//
// Licensed under the Apache 2.0 License
// See accompanying license file or http://apache.org/
//
(function(){
  
    var TIMEOUT = 1000;
    var canChange = true;
    
    var MuteToggle = function() {
    
    };
    
    MuteToggle.prototype = {
        preload : function(entityID) {
        
        },
        mousePressOnEntity : function() {
            if (canChange){ 
                canChange = false;
                Audio.muted = !Audio.muted;
                Script.setTimeout(function(){
                    canChange = true;
                }, TIMEOUT);
            }
        }
    };
    
    return new MuteToggle();

});