Scriptname FCC_P0_InventoryProbe extends Quest
;
; P0 read-only owned ship inspector.
; Attach to a CK quest and run manually. No ship is spawned or modified.
; Starfield 1.16.244: NOT COMPILED / NOT TESTED IN GAME.
;
Function ProbeOwnedShips()
    SpaceshipReference[] ownedShips = Game.GetPlayerOwnedShips()
    SpaceshipReference homeShip = Game.GetPlayerHomeSpaceShip()

    Debug.Trace("[FCC P0] Owned ship count: " + ownedShips.Length)
    Debug.Trace("[FCC P0] Home ship: " + homeShip)

    Int i = 0
    While i < ownedShips.Length
        SpaceshipReference shipRef = ownedShips[i]
        If shipRef != None
            Debug.Trace("[FCC P0] ship index=" + i + " ref=" + shipRef + " home=" + (shipRef == homeShip))
        Else
            Debug.Trace("[FCC P0] ship index=" + i + " is NONE")
        EndIf
        i = i + 1
    EndWhile
EndFunction
