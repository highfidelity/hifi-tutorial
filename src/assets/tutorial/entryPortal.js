(function(){
    this.preload = function(entityID) {
        print("entryPortal.js | Preload");
    }

    this.enterEntity = function(entityID) {
        print("entryPortal.js | enterEntity");

        print("entryPortal.js | sending message to tutorialZone");
        Entities.callEntityMethod("{f482faa7-2918-4d83-8b68-e5ea60cc4af5}", "onEnteredEntryPortal");
        print("entryPortal.js | done sending message to tutorialZone");

        location.goToEntry();
    };

    this.leaveEntity = function(entityID) {
        print("portal.js | leaveEntity");
    };
})
