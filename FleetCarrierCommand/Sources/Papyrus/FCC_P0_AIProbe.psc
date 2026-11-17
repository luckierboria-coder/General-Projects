Scriptname FCC_P0_AIProbe extends Quest
;
; DANGEROUS EXPERIMENTAL P0 PROBE - source only.
; This does NOT deploy a stored ship, attach an Escort package, or make a fleet.
; NEVER use with a production save. Manually confirm both test ships are
; already present/loaded in the same visible space scene.
;
; Owned ship indices are only ephemeral P0 selectors, NOT persistent identities.
Int Property ProbeShipIndex = -1 Auto
Int Property TargetShipIndex = -1 Auto
Bool Property MutationsEnabled = False Auto

Function RunAIProbe()
    If MutationsEnabled == False
        Debug.Trace("[FCC P0] Refused RunAIProbe: MutationsEnabled is false")
        Return
    EndIf

    SpaceshipReference[] ships = Game.GetPlayerOwnedShips()
    If ProbeShipIndex < 0 || ProbeShipIndex >= ships.Length
        Debug.Trace("[FCC P0] Refused RunAIProbe: bad ProbeShipIndex")
        Return
    EndIf

    SpaceshipReference probeShip = ships[ProbeShipIndex]
    SpaceshipReference homeShip = Game.GetPlayerHomeSpaceShip()
    If probeShip == None || probeShip == homeShip
        Debug.Trace("[FCC P0] Refused RunAIProbe: invalid or Home Ship")
        Return
    EndIf

    Debug.Trace("[FCC P0] Enabling AI on non-home test ship " + probeShip)
    probeShip.EnableAI()
    probeShip.EvaluatePackage()
    Debug.Trace("[FCC P0] IsAIEnabled=" + probeShip.IsAIEnabled())
    Debug.Trace("[FCC P0] Note: enabled AI does not prove unmanned flight")
EndFunction

Function RunOneShotPathProbe()
    If MutationsEnabled == False
        Debug.Trace("[FCC P0] Refused path probe: MutationsEnabled is false")
        Return
    EndIf

    SpaceshipReference[] ships = Game.GetPlayerOwnedShips()
    If ProbeShipIndex < 0 || ProbeShipIndex >= ships.Length
        Debug.Trace("[FCC P0] Refused path probe: bad ProbeShipIndex")
        Return
    EndIf
    If TargetShipIndex < 0 || TargetShipIndex >= ships.Length
        Debug.Trace("[FCC P0] Refused path probe: bad TargetShipIndex")
        Return
    EndIf
    If ProbeShipIndex == TargetShipIndex
        Debug.Trace("[FCC P0] Refused path probe: identical ships")
        Return
    EndIf

    SpaceshipReference probeShip = ships[ProbeShipIndex]
    SpaceshipReference targetShip = ships[TargetShipIndex]
    SpaceshipReference homeShip = Game.GetPlayerHomeSpaceShip()
    If probeShip == None || targetShip == None || probeShip == homeShip || targetShip == homeShip
        Debug.Trace("[FCC P0] Refused path probe: invalid or Home Ship")
        Return
    EndIf

    Debug.Trace("[FCC P0] One-shot path from " + probeShip + " to " + targetShip)
    Int result = probeShip.PathToReference(targetShip, 0.35, 0.35, 650.0, False)
    Debug.Trace("[FCC P0] One-shot PathToReference returned: " + result)
    Debug.Trace("[FCC P0] This is not a persistent Follow/Escort AI Package")
EndFunction
