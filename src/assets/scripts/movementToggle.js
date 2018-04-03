//
// movementToggle.js
// 
// Author: Liv Erickson
// Copyright High Fidelity 2018
//
// Licensed under the Apache 2.0 License
// See accompanying license file or http://apache.org/
//
(function(){
  
    var FILE_MENU_OPTION = "Advanced Movement For Hand Controllers";
    var SETTINGS_NAME = "advancedMovementForHandControllersIsChecked";
    var TIMEOUT = 1000;
    
    var isActive;
    var canChange = true;
    
   
    var AdvancedMovementToggle = function() {
    
    };
    
    var switchControlMechanics = function() {
        // avoid duplicate events
        isActive = !isActive;
        Menu.setIsOptionChecked(FILE_MENU_OPTION, isActive);  
    };
    
    AdvancedMovementToggle.prototype = {
        preload : function(entityID) {
            isActive = Settings.getValue(SETTINGS_NAME);
        
        },
        mousePressOnEntity : function() {
            if (canChange){ 
                canChange = false;
                switchControlMechanics();
                Script.setTimeout(function(){
                    canChange = true;
                }, TIMEOUT);
            }
        }
    };
    
    return new AdvancedMovementToggle();

});