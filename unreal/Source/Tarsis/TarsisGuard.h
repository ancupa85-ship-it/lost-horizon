// Lost Horizon: De Profundis — núcleo del sigilo (fase 2 del plan de migración).
// Guardia de la base de Tarsis: ronda por puntos, vista con cono, distancia y luz, «?» y «!», alerta y captura.
// Se copia en Source/<Módulo>/Tarsis/ del proyecto de Unreal (ver unreal/README.md).
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "TarsisGaspTurn.h"
#include "TarsisGuard.generated.h"

class UStaticMeshComponent;
class UTextRenderComponent;
class USkeletalMesh;
class UAnimationAsset;

UENUM(BlueprintType)
enum class ETarsisGuardState : uint8
{
	Patrol     UMETA(DisplayName = "Ronda"),
	Suspicious UMETA(DisplayName = "Mosqueado"),
	Alert      UMETA(DisplayName = "Alerta"),
	Search     UMETA(DisplayName = "Buscando"),
	Return     UMETA(DisplayName = "Volviendo"),
	Down       UMETA(DisplayName = "Derribado")
};

UCLASS()
class ATarsisGuard : public ACharacter
{
	GENERATED_BODY()
	// el director pone a los guardias en su ronda al cargar un punto de control (SetState es privado)
	friend class ATarsisDirector;

public:
	ATarsisGuard();
	virtual void Tick(float DeltaSeconds) override;

	/** Puntos de la ronda en coordenadas del mundo (los pone tools/unreal/guardias.py). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Ronda", meta = (MakeEditWidget = "true"))
	TArray<FVector> PatrolPoints;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Ronda")
	float WaitAtPoint = 2.0f;

	/** Espera en cada punto (s), si se quiere distinta por punto; donde falte se usa WaitAtPoint. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Ronda")
	TArray<float> PatrolWaits;

	/** Paso de ronda (cm/s). 175 con las animaciones del maniquí (andar a ~280): zancada natural sin parecer cámara lenta. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Ronda")
	float WalkSpeed = 175.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Ronda")
	float RunSpeed = 430.0f;

	/** Hasta dónde ve con buena luz (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Vista")
	float ViewDistance = 2000.0f;

	/** Medio ángulo del cono de visión (grados). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Vista")
	float ViewHalfAngle = 50.0f;

	/** Más cerca de esto te nota aunque estés a su espalda (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Vista")
	float NearDistance = 220.0f;

	/** Cuánto sube la sospecha por segundo con visibilidad 1 (1 = alerta). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Vista")
	float SuspicionRate = 0.9f;

	/** Cuánto baja por segundo cuando no te ve. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Vista")
	float SuspicionDecay = 0.2f;

	/** Distancia a la que te atrapa en alerta (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Vista")
	float CatchDistance = 130.0f;

	/** Centinela de torre: no anda; barre con la vista (y con su foco) a un lado y a otro y, si te ve, avisa a los de abajo. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Torre")
	bool bTowerSentry = false;
	/** Lo que tarda el de la torre en estar seguro de lo que ve en su foco, frente a un guardia de abajo (0,45: unos 3-4 s en facil). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Torre")
	float TowerGain = 0.45f;

	/** Foco de la torre, que gira con el centinela (lo pone tools/unreal/guardias.py). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Torre")
	TObjectPtr<AActor> TowerLight;

	/** Hacia dónde mira la torre (yaw en grados) y cuánto barre a cada lado. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Torre")
	float TowerYaw = 0.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Torre")
	float TowerSweep = 54.0f;

	/** Recorrido del foco por el suelo (tanda 26): puntos del mundo que el haz va pisando, siempre igual, para que se
	 *  pueda aprender. Los pone tools/unreal/guardias.py desde mision1.json. Con menos de dos puntos, el foco barre a
	 *  un lado y a otro como antes (TowerYaw y TowerSweep). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Torre", meta = (MakeEditWidget = "true"))
	TArray<FVector> SweepPath;

	/** Cerrado (del último punto vuelve al primero) o de ida y vuelta. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Torre")
	bool bSweepLoop = true;

	/** A qué paso recorre el suelo la mancha del foco (cm/s). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Torre")
	float SweepSpeed = 350.0f;

	/** Segundos que el foco se queda quieto en cada punto del recorrido (donde falte, no se para). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Torre")
	TArray<float> SweepStops;

	/** En qué segundo de su vuelta arranca (fijo: cada partida empieza igual, y las dos torres van desacompasadas). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Torre")
	float SweepPhase = 0.0f;

	/** Distancia (cm) a la que el foco pinta con los lúmenes que trae del nivel: más lejos sube y más cerca baja, para
	 *  que la mancha se vea igual de fuerte en todo el recorrido y no queme lo que tiene cerca. Para el sigilo cuenta
	 *  siempre lo mismo (BeamLumens). 0 = no se toca la intensidad. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Torre")
	float SweepRefDist = 0.0f;

	/** Hasta dónde acude el foco cuando un guardia de suelo da la alarma (cm desde la torre) y cuánto se queda (s). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Torre")
	float BeamCallRadius = 4500.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Torre")
	float BeamCallSeconds = 8.0f;

	/** Punto del suelo al que apunta el foco ahora. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Torre")
	FVector SweepAim = FVector::ZeroVector;

	/** Lúmenes del foco para el sigilo (los que traía del nivel al empezar; lo pintado va aparte). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Torre")
	float BeamLumens = 0.0f;

	/** Segundos que le quedan al foco en el sitio de una alarma (0 = sigue su recorrido). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Torre")
	float BeamCallT = 0.0f;

	/** Punto del recorrido en el segundo T de la vuelta (con sus paradas). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Torre")
	FVector SweepPointAt(float T) const;

	/** Lo que dura una vuelta entera del foco (s); 0 si no hay recorrido. */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Torre")
	float SweepPeriod() const;

	/** Segundo de la vuelta por el que va el foco. */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Torre")
	float SweepTime() const { return TowerT; }

	/** Alarma abajo: el foco deja su recorrido y se va a Where durante Seconds; luego vuelve al punto más cercano.
	 *  Solo si el centinela estaba tranquilo y el sitio le queda a mano (BeamCallRadius). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Torre")
	bool CallBeam(const FVector& Where, float Seconds);

	/** Ajuste 26b: una luz que pinta menos de lo que cuenta (los faros del camión). Lumens son los que valen para el
	 *  sigilo, antes del «luz_fuerte»; 0 la borra de la lista. */
	static void SetStealthLumens(const AActor* LightActor, float Lumens);

	/** Un compañero (por ejemplo una torre) da la voz: viene corriendo a ese sitio. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	void Alarm(const FVector& Where);

	/** Ha oído un ruido (una piedra): se acerca despacio a mirar y busca un rato; luego vuelve a su ronda. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	void HearNoise(const FVector& Where);

	/** De tu parte (Ramos, si aceptas llevarlo contigo): no te ve ni da la voz por los cuerpos. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Estado")
	bool bAlly = false;

	/** Tanda 37: a que distancia te tiene a tiro y en que radio busca donde cubrirse (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armado")
	float ArmedRange = 1800.0f;
	/** Tanda C: el centinela de la torre dispara (desde la boca de su M14) si huyes a menos de ArmedRange * TowerRangeMul. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armado")
	bool bTowerShoots = true;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armado")
	float TowerRangeMul = 1.4f;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Armado")
	int32 TowerShots = 0;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armado")
	float CoverRadius = 900.0f;
	/** Segundos que aguanta en su sitio cuando te pierde de vista, antes de avanzar andando. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armado")
	float ArmedHoldSeconds = 3.0f;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Armado")
	bool bHasCover = false;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Armado")
	FVector CoverLoc = FVector::ZeroVector;

	/** Deja su ronda y se va a Where, donde se queda (Ramos al portillo de la marisma). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	void GoTo(const FVector& Where);

	/** Base en guardia tras una alarma: la sospecha sube más deprisa (lo pone el director). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadWrite, Category = "Tarsis|Estado")
	float AlertBoost = 1.0f;

	/** Dónde cayó derribado (adonde irán a buscarlo por radio si no contesta). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Estado")
	FVector KnockLoc = FVector::ZeroVector;

	/** Segundos que lleva en el suelo. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	float DownTime() const { return State == ETarsisGuardState::Down ? StateT : 0.0f; }

	/** Va a mirar por un ruido (y no por la vista). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	bool IsInvestigating() const { return bInvestigate; }

	/** Se queda quieto Seconds segundos (mientras habla contigo). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	void Hold(float Seconds);

	/** Recado del director (tanda 22: mirar los papeles del camión en el control): deja la ronda, va a Where, se queda allí
	 *  mirando hacia Face y, a los Seconds segundos como mucho (o con EndErrand), vuelve a su ronda. Solo lo acepta si está
	 *  de ronda o volviendo a ella; en cuanto ve u oye algo, el recado se acaba (manda la sospecha, como siempre). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	bool Errand(const FVector& Where, const FVector& Face, float Seconds);

	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	void EndErrand();

	UFUNCTION(BlueprintPure, Category = "Tarsis")
	bool IsOnErrand() const { return bErrand; }

	/** Ya ha llegado al sitio del recado. */
	UFUNCTION(BlueprintPure, Category = "Tarsis")
	bool AtErrand() const { return bErrand && bErrandThere; }

	/** El recado se acaba dentro de Seconds como mucho (para que termine un gesto antes de volver a la ronda). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	void EndErrandIn(float Seconds) { if (bErrand) ErrandT = FMath::Min(ErrandT, Seconds); }

	/** Gesto con los brazos (tanda 24), encima de la animación que tenga: «alto» (mano en alto; también andando),
	 *  «papeles» (tiende la mano), «leer» (mira lo que tiene en las manos), «pase» (da paso con el brazo hacia el punto
	 *  Toward) y «lona» (levanta el brazo para mirar dentro de la caja). Dura Seconds; se deshace solo si deja de estar
	 *  tranquilo o echa a andar. No cambia lo que ve ni lo que oye. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Cuerpo")
	void PlayGesture(FName Name, float Seconds, FVector Toward = FVector::ZeroVector);

	/** Gesto que se le ve ahora (None si ninguno). */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Cuerpo")
	FName CurrentGesture() const { return GestureW > 0.05f ? Gesture : NAME_None; }

	/** Cuánto pesa el gesto ahora, 0-1 (entra y sale suave). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Cuerpo")
	float GestureW = 0.0f;

	/** Bastón luminoso de señales (tanda 25): lo lleva encendido en la mano derecha durante Seconds (se renueva
	 *  llamando otra vez). Sigue al antebrazo, así que con «alto» queda en alto y con «pase» hace la señal. Se guarda
	 *  solo si deja la ronda. Su luz no cuenta para el sigilo. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Cuerpo")
	void HoldBaton(float Seconds);

	/** Lleva el bastón encendido ahora. */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Cuerpo")
	bool BatonOn() const;

	/** Largo del bastón (cm) y lo que alumbra (lúmenes: poco, tiñe de rojo el brazo y la cara del que lo lleva). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cuerpo")
	float BatonLength = 36.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cuerpo")
	float BatonLumens = 16.0f;

	/** Gestos que ha hecho, por orden (pruebas). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Cuerpo")
	TArray<FName> GestureLog;

	/** Altura de una mano sobre sus pies, en cm (pruebas: con «alto» la derecha pasa de la cabeza). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Cuerpo")
	float HandHeight(bool bRight = true);

	/** Marcado con los prismáticos: el HUD muestra su nombre y estado aunque esté detrás de una pared. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadWrite, Category = "Tarsis|Estado")
	bool bMarked = false;

	/** Derribado por la espalda: cae y duerme KnockOutTime segundos; si otro guardia lo ve, da la alarma. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	void KnockOut();
	/** Tanda C, para las pruebas: se despierta ya (como al acabar KnockOutTime). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	void WakeNow() { if (State == ETarsisGuardState::Down) WakeUp(); }

	/** Se le puede derribar ahora desde la posición de Who (cerca, por la espalda, sin ser centinela ni estar ya caído). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	bool CanBeTakenDown(const AActor* Who) const;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis")
	float KnockOutTime = 100.0f;

	/** Nombre para los avisos («Ibarra»...). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis")
	FString GuardName;

	/** Ya lo ha encontrado otro guardia. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Estado")
	bool bFound = false;

	/** Cuerpo con esqueleto (personas del juego web, importadas por tools/unreal/personas.py). Sin él se ve el cilindro provisional. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cuerpo")
	TObjectPtr<USkeletalMesh> BodyMesh;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cuerpo")
	TObjectPtr<UAnimationAsset> IdleAnim;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cuerpo")
	TObjectPtr<UAnimationAsset> WalkAnim;

	/** Mezcla de quieto a andar según la velocidad (BlendSpace1D, lo crea tools/unreal/personas.py). Si está, sustituye a IdleAnim/WalkAnim. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cuerpo")
	TObjectPtr<class UBlendSpace> MoveBlend;

	/** Apuntando (en alerta cuando se para). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cuerpo")
	TObjectPtr<UAnimationAsset> AimAnim;

	/** Caer al suelo (derribado). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cuerpo")
	TObjectPtr<UAnimationAsset> DownAnim;

	/** Velocidad (cm/s) a la que la animación de andar no patina; con más velocidad se reproduce más rápido. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cuerpo")
	float WalkAnimSpeed = 150.0f;

	/** Reconstruye los datos de ejecución (segmentos) de una mezcla creada por script. Solo en el editor: Python puede
	 *  rellenar SampleData, pero el motor solo llama a ResampleData desde el editor de mezclas; sin eso la mezcla no
	 *  avanza en el juego y el guardia se desliza con una pose fija. Lo usa tools/unreal/animaciones.py. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Editor")
	static bool RebuildBlendSpace(class UBlendSpace* BlendSpace);

	/** Velocidad (cm/s) de la muestra de trotar en MoveBlend (tools/unreal/animaciones.py); 0 = la mezcla solo llega a andar. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cuerpo")
	float RunAnimSpeed = 0.0f;

	/** Tanda A (2026-11-21): con el Animation Blueprint del Game Animation Sample de Epic (Motion Matching). Solo actúa
	 *  si la clase del guardia implementa BPI_SandboxCharacter_Pawn (la copia reparentada BP_GuardiaGASP) y están los
	 *  assets migrados. Entonces GetMesh() pasa a ser el maniquí UEFN oculto que corre el ABP y el cuerpo de la persona
	 *  (GaspBody) copia su pose con ABP_GenericRetarget y el IK Retargeter RTG_UEFN_<persona>. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cuerpo")
	bool bGaspAnim = true;

	/** IK Retargeter del maniquí UEFN a esta persona (si falta se busca RTG_UEFN_<persona> en /Game/Tarsis/Anim). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cuerpo")
	TObjectPtr<UObject> GaspRetargeter;

	/** Giro extra (grados) del cuerpo de la persona respecto al maniquí que conduce, por si el retarget lo deja de lado. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cuerpo")
	float GaspBodyYaw = 0.0f;

	/** Velocidad (cm/s) a partir de la cual se le pide al ABP el paso de correr en vez del de andar. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cuerpo")
	float GaspRunFrom = 320.0f;

	/** Aceleración y frenada del CharacterMovementComponent con el GASP (las bases de Motion Matching se grabaron con
	 *  arranques y paradas suaves; con los valores de la plantilla el guardia arranca en seco y el ABP elige mal). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cuerpo")
	float GaspMaxAcceleration = 800.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cuerpo")
	float GaspBrakingDeceleration = 500.0f;

	/** Frenada al pararse (sin aceleración pedida), como el personaje del GASP. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cuerpo")
	float GaspStopDeceleration = 2000.0f;

	UFUNCTION(BlueprintPure, Category = "Tarsis|Cuerpo")
	bool UsesGasp() const { return GaspBody != nullptr; }

	/** Tanda A, novena: la detención. Con bSceneLock el guardia no toca su animación (GaspTick no hace nada): ScenePlay
	 *  pone una animación suelta en el maniquí del GASP (la persona la copia con el retarget) y SceneEnd le devuelve el
	 *  ABP; el director lo agacha y lo suelta al acabar. */
	bool bSceneLock = false;
	bool ScenePlay(class UAnimSequenceBase* A);
	void SceneEnd();

	// ---- tanda B (TarsisArmas.cpp): el fusil. Un M14 (/Game/Tarsis/Armas/M14/SM_M14, CC0 de Stein Games) en la mano
	// derecha del cuerpo visible; de cintura para arriba, la pose de fusil de Lyra retargeteada a la persona
	// (MM_Rifle_Idle_Hipfire_<persona> de ronda, MM_Rifle_Idle_ADS_<persona> en alerta) encima de la locomoción del GASP.
	/** Apagado, sin fusil (como antes: el fogonazo sale de delante del pecho). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armas")
	bool bRifleRule = true;
	/** Dónde va el fusil respecto al hueso de la mano derecha (cm y grados, en el espacio del hueso). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armas")
	FVector RifleGripLoc = FVector(-3.0f, 2.0f, 0.0f);
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armas")
	FRotator RifleGripRot = FRotator(2.2f, 130.8f, -64.8f);   // medido en el PC: canon hacia delante y un poco abajo, a la cadera
	/** El agarre apuntando (pose ADS de Lyra): la mano gira distinto, el canon recto. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armas")
	FRotator RifleAimGripRot = FRotator(2.6f, 127.9f, -56.1f);
	/** Mano izquierda al guardamanos con IK de dos huesos (en el espacio del fusil: X lado, Y a lo largo del canon, Z arriba). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armas")
	bool bRifleLeftIK = true;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armas")
	FVector RifleLeftHand = FVector(-4.0f, 40.0f, -3.0f);
	/** Cuánto manda la pose de fusil en el torso (los brazos van enteros con ella). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armas")
	float RifleSpineWeight = 0.6f;
	/** Tanda C: andando manda menos (deja pasar el giro y el vaivén del torso de la locomoción). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armas")
	float RifleSpineWeightMoving = 0.3f;
	/** Tanda C: el fusil se coloca respecto al hombro derecho y las dos manos van a él con IK (si no, donde lo deje la mano
	 *  de la pose de Lyra). Culata: adelante (X), a la derecha (Y) y arriba (Z) del hombro, en cm; canon: cabeceo y giro
	 *  (grados; negativo, hacia abajo y hacia la izquierda). A la cadera, culata bajo la axila; apuntando, al hombro. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armas")
	bool bRifleHold = true;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armas")
	FVector RifleHipButt = FVector(4.0f, -4.0f, -15.0f);
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armas")
	float RifleHipPitch = -12.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armas")
	float RifleHipYaw = -10.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armas")
	FVector RifleAimButt = FVector(2.0f, -6.0f, -2.0f);
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armas")
	float RifleAimPitch = 0.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armas")
	float RifleAimYaw = -2.0f;
	/** Del origen del M14 (la muñeca de la culata) al final de la culata, a lo largo del cañón (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armas")
	float RifleButtBack = 24.5f;
	/** El vaivén al andar: arriba y abajo con cada paso, de lado con cada zancada (cm) y ladeo (grados); largo del paso. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armas")
	float RifleSwayBob = 1.4f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armas")
	float RifleSwaySide = 1.6f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armas")
	float RifleSwayRoll = 3.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armas")
	float RifleStepLength = 75.0f;
	/** La culata y el hombro derecho, en el mundo (pruebas: apuntando, la culata al hombro). */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Armas")
	FVector RifleButt() const;
	UFUNCTION(BlueprintPure, Category = "Tarsis|Armas")
	FVector RifleShoulder() const;
	/** Cuánto se mueve ahora el fusil por el vaivén del paso (0 parado, 1 andando del todo). */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Armas")
	float RifleSway() const { return RifleMoveW; }
	UFUNCTION(BlueprintPure, Category = "Tarsis|Armas")
	bool HasRifle() const { return Rifle != nullptr; }
	/** Peso actual de la pose de fusil (0 suelta, 1 entera). */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Armas")
	float RiflePoseWeight() const { return RifleW; }
	/** La boca del cañón (socket Muzzle del M14); sin fusil, delante del pecho como antes. */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Armas")
	FVector RifleMuzzle() const;
	/** Apunta con la pose de alerta (la de apuntar con el fusil). */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Armas")
	bool RifleAiming() const { return bRifleAim; }
	UPROPERTY()
	TObjectPtr<class UStaticMeshComponent> Rifle;
	UPROPERTY()
	TObjectPtr<USkeletalMeshComponent> RifleRef;   // la persona oculta que hace la pose de fusil
	UPROPERTY()
	TObjectPtr<class UAnimSequenceBase> RifleIdleAnim;
	UPROPERTY()
	TObjectPtr<class UAnimSequenceBase> RifleAimAnim;
	TArray<FName> RifleBones;    // de spine_02 hacia arriba, sin cuello ni cabeza, padres antes que hijos
	TArray<bool> RifleBoneIsSpine;
	FName RifleRootBone;         // spine_01: la pose se pone relativa a él
	float RifleW = 0.0f;
	float RifleAimW = 0.0f;
	float RifleMoveW = 0.0f;
	float RiflePhase = 0.0f;
	FTransform RifleCSNow = FTransform::Identity;   // el fusil, en el espacio de la malla visible, tras el IK
	bool bRifleAim = false;
	bool RifleHoldTransform(FTransform& Out) const;
	/** Tanda D: el fusil a la espalda acariciando al lobo; la altura de la persona para escalar los sitios del fusil; y el
	 *  brazo que no se estira de mas (RifleMaxReach del largo del brazo). */
	bool RifleSlungTick(float DeltaSeconds);
	bool bRifleSlung = false;
	float RiflePersonaScale = 1.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armas")
	float RifleRefShoulder = 145.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armas")
	float RifleMaxReach = 0.94f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armas")
	float RifleSlingBack = 16.0f;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Armas")
	int32 RifleReachClamps = 0;
	UFUNCTION(BlueprintPure, Category = "Tarsis|Armas")
	bool RifleOnBack() const;
	UFUNCTION(BlueprintPure, Category = "Tarsis|Armas")
	float PersonaScale() const { return RiflePersonaScale; }
	void RifleArmIK(int32 Side, const FVector& Target, const FTransform* HandCS, float W);
	void SetupRifle();
	void RifleTick(float DeltaSeconds);

	// ---- tanda B (TarsisPerro.cpp): acariciar al lobo amigo. Lo decide el director; el guardia va con un recado (Errand)
	// hasta el lobo, se agacha mirandolo PetSeconds y vuelve a su ronda. Mientras, mira al suelo: ve mucho menos.
	/** Lo que ve (fraccion de su vista normal) mientras lo acaricia. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Lobo")
	float PetViewMul = 0.35f;
	/** Tanda C: el punto al que va, respecto al lomo del lobo (cm por su lado; negativo, pasado el lomo): el recado
	 *  acaba a 70 cm del punto y el guardia aún se pasa unos 40: con -12 se queda a ~50 cm y la mano llega al lomo. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Lobo")
	float PetStandOff = -12.0f;
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Lobo")
	bool StartPet(const FVector& DogAt, float Seconds);
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Lobo")
	void StopPet();
	/** Va a acariciarlo o lo esta acariciando. */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Lobo")
	bool IsPetting() const { return bPetting; }
	/** Ya esta agachado junto al lobo. */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Lobo")
	bool PetCrouched() const { return bPetting && PetT > 0.0f; }
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Lobo")
	float PetT = 0.0f;
	/** Cuando acabo de acariciarlo por ultima vez (segundos de mundo). */
	float PetDoneAt = -1e9f;
	bool bPetting = false;
	float PetSeconds = 6.0f;
	FVector PetDog = FVector::ZeroVector;
	void PetTick(float DeltaSeconds);
	/** Tanda D: relevo. Baja de la torre (queda como guardia de suelo al pie, Ground) o sube a tomar el puesto de From. */
	void LeaveTowerPost(const FVector& Ground);
	void TakeTowerPost(ATarsisGuard* From, const FVector& Post, const FRotator& Rot, AActor* Light);
	/** Tanda D: va siguiendo un rastro de huellas (lo lleva el director). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Huellas")
	bool bTrackingPrints = false;
	/** Tanda C: adónde va la mano izquierda al acariciar (el lomo del lobo con un vaivén; lo pone el director). */
	FVector PetHandWorld = FVector::ZeroVector;
	float PetHandW = 0.0f;
	UFUNCTION(BlueprintPure, Category = "Tarsis|Lobo")
	float PetHandWeight() const { return PetHandW; }
	/** La mano izquierda, en el mundo (pruebas: acariciando, sobre el lomo). */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Lobo")
	FVector LeftHandLocation() const;

	// ---- tanda C (TarsisFisica.cpp): física del cuerpo. El maniquí del GASP que conduce (GetMesh, con PA_UEFN_Mannequin)
	// hace la física y la persona la copia (retarget), como Cuttlas en la detención.
	// - Un golpe (el empujón) o el dardo: reacción de Lyra según de dónde viene (MM_HitReact_*) y, de spine_01 hacia
	//   arriba, cuerpos simulados con animación física (UPhysicalAnimationComponent) que se van apagando.
	// - Dormido (dardo o derribo): cae con ragdoll y se queda en reposo; al despertar, la pose pasa de la física a la
	//   animación en WakeBlendSeconds.
	// - Solo cerca del jugador (PhysicsNear): los de lejos caen con la animación de siempre.
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Fisica")
	bool bPhysicsRule = true;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Fisica")
	float PhysicsNear = 3500.0f;
	/** Cuánto manda la física en la reacción al golpe (0-1), cuánto dura (s) y el empujón (cm/s). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Fisica")
	float HitBlend = 0.6f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Fisica")
	float HitSeconds = 0.55f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Fisica")
	float HitImpulse = 260.0f;
	/** El dardo: lo que dura la reacción antes de caer con física (s), y el empujón de la caída (cm/s). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Fisica")
	float DartFallDelay = 0.35f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Fisica")
	float RagdollPush = 140.0f;
	/** De la física a la animación al despertar (s). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Fisica")
	float WakeBlendSeconds = 0.8f;
	/** Reacción a un golpe que viaja en la dirección Dir (mundo). bHeavy: la variante «Med» de Lyra. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Fisica")
	void HitReact(FVector Dir, bool bHeavy = false);
	/** El dardo le alcanza viniendo en la dirección Dir: reacción y, tras DartFallDelay, ragdoll (lo llama el director
	 *  antes de KnockOut). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Fisica")
	void DartHit(FVector Dir);
	UFUNCTION(BlueprintPure, Category = "Tarsis|Fisica")
	bool IsRagdoll() const { return bRagdoll; }
	/** Reaccionando a un golpe (animación o cuerpos con física). */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Fisica")
	bool HitReacting() const { return HitAnimT > 0.0f || HitPhysT > 0.0f; }
	UFUNCTION(BlueprintPure, Category = "Tarsis|Fisica")
	float HitPhysicsWeight() const { return HitPhysT > 0.0f ? HitBlend * HitPhysT / FMath::Max(HitSeconds, 0.01f) : 0.0f; }
	UFUNCTION(BlueprintPure, Category = "Tarsis|Fisica")
	FString LastHitAnim() const { return HitAnimName; }
	/** La pelvis del cuerpo (con ragdoll, donde ha caído). */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Fisica")
	FVector PelvisLocation() const;
	/** Pasando de la física a la animación (al despertar). */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Fisica")
	bool WakeBlending() const { return WakeT > 0.0f; }
	/** Simula física ahora mismo (ragdoll o reacción): para medir cuántos cuerpos cuestan a la vez. */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Fisica")
	bool PhysicsActive() const { return bRagdoll || HitPhysT > 0.0f; }
	/** Lo están arrastrando con física (lo pone el director): no se duerme el ragdoll. */
	bool bPhysDragged = false;
	UPROPERTY()
	TObjectPtr<class UPhysicalAnimationComponent> PhysAnim;
	UPROPERTY()
	TObjectPtr<class UAnimSequenceBase> HitAnims[8];   // Front/Back/Left/Right, Lgt y Med
	bool bHitAnimsTried = false;
	bool bRagdoll = false;
	bool bRagdollSlept = false;
	float RagdollT = 0.0f;
	float RagdollPendingT = -1.0f;
	FVector PendingFallDir = FVector::ZeroVector;
	float HitAnimT = 0.0f;
	float HitPhysT = 0.0f;
	FString HitAnimName;
	FTransform DriverRel = FTransform::Identity;   // dónde va el maniquí respecto a la cápsula
	bool bDriverRelSaved = false;
	TArray<FTransform> WakeFrom;                   // la pose tumbada (mundo) de la que se parte al despertar
	float WakeT = 0.0f;
	void PhysicsTick(float DeltaSeconds);
	void StartRagdoll();
	void StopRagdoll(bool bBlend);
	void WakeBlendTick(float DeltaSeconds);
	bool PhysicsCanRun() const;
	void LoadHitAnims();
	void PhysicsBodies(bool bOn);
	// tanda D: precalentar los cuerpos, levantarse por agachado, y de que lado quedo
	void PhysicsWarm();
	FVector BodyFront() const;
	bool bPhysWarm = false;
	float FrontSign = 1.0f;
	float GetUpT = 0.0f;
	bool bLastFaceUp = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Fisica")
	bool bPhysWarmRule = true;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Fisica")
	float GetUpKneelSeconds = 0.9f;
	/** Lo que tardo en precalentar sus cuerpos (ms). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Fisica")
	float PhysWarmMs = 0.0f;
	UFUNCTION(BlueprintPure, Category = "Tarsis|Fisica")
	bool PhysicsWarmed() const { return bPhysWarm; }
	UFUNCTION(BlueprintPure, Category = "Tarsis|Fisica")
	bool LastFaceUp() const { return bLastFaceUp; }
	UFUNCTION(BlueprintPure, Category = "Tarsis|Fisica")
	bool GettingUp() const { return GetUpT > 0.0f || WakeT > 0.0f; }

	/** Giro en el sitio parado (TarsisGaspTurn.h): con las piernas a GaspTurnFrom grados o más de donde mira, WantsToAim
	 *  un momento para que el ABP gire en el sitio. Más bajo que en Cuttlas: el guardia va en modo «orientar al
	 *  movimiento», sin aim offset, y parado no gira ni el torso; solo la cabeza se adelanta. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cuerpo")
	float GaspTurnFrom = 60.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cuerpo")
	float GaspTurnRelease = 15.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cuerpo")
	float GaspTurnMaxSeconds = 1.5f;
	UFUNCTION(BlueprintPure, Category = "Tarsis|Cuerpo")
	bool GaspTurnAiming() const { return GaspTurn.bAim; }
	/** Grados que las piernas van por detrás de hacia dónde mira el actor (del hueso raíz del maniquí que conduce). */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Cuerpo")
	float GaspTurnDelta() const { return GaspTurn.Delta; }

	/** La malla con el esqueleto de la persona que se anima (de ella copian el cuerpo visible, los pasos y los gestos). */
	USkeletalMeshComponent* AnimBody() const;

	/** Giro actual de cabeza y cuello respecto al cuerpo (grados, + a la derecha): mira hacia un ruido, barre al buscar. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Cuerpo")
	float LookYaw = 0.0f;

	/** Pasos que ha dado (pie que apoya, según la animación): para las pruebas y el sonido de sus pasos. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Cuerpo")
	int32 StepsTaken = 0;

	/** Gira en el sitio dando pasos (la animación de andar despacio mientras rota). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Cuerpo")
	bool bTurnStepping = false;

	/** Empujón de frente (E, si aún no está en alerta): aturdido Seconds segundos, sin ver; se le puede derribar por
	 *  cualquier lado. Si nadie lo derriba, al rehacerse va a por ti (alerta hacia donde estabas). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	void Stun(float Seconds);

	UFUNCTION(BlueprintPure, Category = "Tarsis")
	bool IsStunned() const { return StunT > 0.0f; }

	/** Ha visto un cuerpo y va a mirarlo antes de dar la alarma (se agacha 2 s sobre él y avisa por radio). */
	UFUNCTION(BlueprintPure, Category = "Tarsis")
	bool IsCheckingBody() const { return BodyTarget != nullptr; }

	/** Segundos que lleva agachado sobre el cuerpo (para las pruebas). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Estado")
	float BodyCheckT = 0.0f;

	/** Tiene cuerpo con esqueleto y sus pasos salen de la animación (si no, el director los cuenta por distancia). */
	bool HasFootSync() const { return Pose != nullptr; }

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Estado")
	ETarsisGuardState State = ETarsisGuardState::Patrol;

	/** Sospecha de 0 a 1. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Estado")
	float Meter = 0.0f;

	/** Cuánto ve este guardia al objetivo ahora mismo (0 = nada, 1 = de lleno). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	float Visibility(const AActor* Target) const;

	/** Luz aproximada que recibe un punto (0 = oscuridad, 1 = bien iluminado): farolas, focos e interiores, con sombra. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis", meta = (WorldContext = "WorldContext"))
	static float LightAt(const UObject* WorldContext, FVector Point);

	/** Sombras que echa Who ahora mismo (tanda 26). Por cada luz con sombra que le da de lleno (aporta MinLight o más
	 *  en su pecho) se tiran tres rayos (cabeza, pecho y rodillas: Heights, en cm sobre sus pies) hasta el suelo o la
	 *  pared de detrás. Un punto cuenta si allí esa luz sigue alumbrando y manda sobre las demás (Contrast = lo que
	 *  aporta esa luz entre toda la que llega). Solo las luces que dibujan sombra: lo que el guardia nota es lo que
	 *  tú ves en pantalla. Devuelve cuántos puntos hay. */
	static int32 ShadowsOf(const UObject* WorldContext, const AActor* Who, const TArray<float>& Heights, float MinLight, TArray<FVector>& Tips, TArray<float>& Contrast);

	/** Ha visto una sombra de alguien a quien no ve: la sospecha sube Amount (hasta Cap, nunca hasta la alerta) y, si
	 *  pasa de 0,3, deja la ronda y va a mirar la punta de la sombra (Tip), vuelto hacia donde venía (From). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	bool NoticeShadow(const FVector& Tip, const FVector& From, float Amount, float Cap = 0.55f);

	/** Mosqueado por una sombra (el «?» sale de otro color). */
	UFUNCTION(BlueprintPure, Category = "Tarsis")
	bool IsShadowCurious() const { return bShadow; }

	/** Linterna en la mano (durante el apagón): el cono se ve en la niebla y cuenta como luz para verte. */
	void SetFlashlight(bool bOn);
	UFUNCTION(BlueprintPure, Category = "Tarsis")
	bool HasFlashlightOn() const;
	/** La linterna se queda encendida aunque vuelva a su ronda (el que encontró una farola rota). */
	void KeepFlashlight() { SetFlashlight(true); bDarkTorch = false; bAutoTorch = false; }

	// ---- tanda 31: la linterna según el sitio. En ronda o yendo a mirar algo, si donde pisa no llega luz la enciende;
	// al volver a la luz la guarda. La ves venir de lejos y su cono le alarga la vista: lo oscuro ya no es terreno libre.
	// Lo manda ATarsisDirector::bContextTorch
	/** Lúmenes que pinta la linterna (para el sigilo cuenta siempre 2500). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Linterna")
	float TorchPaintLumens = 700.0f;
	/** Por debajo de esta luz ambiente (0 a 1, sin contar linternas) la enciende; por encima de TorchOffAbove la guarda. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Linterna")
	float TorchOnBelow = 0.26f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Linterna")
	float TorchOffAbove = 0.45f;
	/** La lleva encendida porque está a oscuras (y no por el apagón ni por una farola rota). */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Linterna")
	bool HasAutoTorch() const { return bAutoTorch && HasFlashlightOn(); }
	/** Decide ya (sin esperar al siguiente medio segundo) si le toca linterna. Para las pruebas. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Linterna")
	void AutoTorchNow() { TorchT = 0.0f; TorchLit = 99; TorchOnFor = 999.0f; AutoTorchTick(0.0f); }
	/** Tambien la saca de ronda al aire libre si esta a oscuras (por defecto solo bajo techo o yendo a mirar algo: de
	 *  noche casi toda la base esta a la misma luz de luna y la llevarian siempre encendida). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Linterna")
	bool bTorchOutdoors = false;
	/** Una vez encendida, aguanta al menos estos segundos (no parpadea al cruzar manchas de luz). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Linterna")
	float TorchMinOn = 9.0f;   // tanda 32: con 5 s Ramos la sacaba y guardaba unas 4 veces por minuto en el barracon
	/** Pisa suelo de interior (bajo techo). */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Linterna")
	bool IsIndoors() const;
	/** Luz ambiente en un punto, 0 a 1, sin contar las linternas de los guardias. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Linterna", meta = (WorldContext = "WorldContext"))
	static float AmbientAt(const UObject* WorldContext, FVector Point);
	/** Tanda 42: de dia, el fondo de luz a cielo abierto y bajo techo (0 = noche, fondo 0,12). */
	static void SetDayAmbient(float Open, float Roofed);
	/** De dia la vista llega mas lejos: por cuanto se multiplica la de los de a pie y la de los de torre (1 de noche). */
	static void SetDayView(float Ground, float Tower);
	static void SetContextTorch(bool bOn);
	/** Deslumbrado por tu linterna a bocajarro: aturdido Seconds y luego va a por ti. No repite hasta pasados Again segundos (se tapa los ojos). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Linterna")
	bool Dazzle(float Seconds, float Again);
	UFUNCTION(BlueprintPure, Category = "Tarsis|Linterna")
	bool IsDazzled() const { return bDazzled && StunT > 0.0f; }
	/** La linterna del jugador (o nullptr): con ella encendida se le ve como si estuviera en plena luz. */
	static void SetPlayerTorch(const class USpotLightComponent* L);

	// ---- tanda 28: no entra solo a mirar un ruido donde han roto la farola. Se planta, saca la linterna, pide apoyo
	// por radio y espera al compañero; luego entran los dos. Mientras espera, la zona a oscuras es tuya y el compañero
	// ha dejado su ronda. Lo decide ATarsisDirector::LampsTick (él sabe qué farolas faltan)
	/** Espera plantado a que llegue un compañero antes de entrar a oscuras. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Sigilo")
	bool bWaitBuddy = false;
	/** Va a mirar un ruido y aún nadie ha decidido si entra solo. */
	bool WantsDarkCheck() const { return State == ETarsisGuardState::Suspicious && bInvestigate && !bDarkChecked && !bEscort && !bRepairing && HoldT <= 0.0f; }
	/** Adónde va a mirar. */
	UFUNCTION(BlueprintPure, Category = "Tarsis")
	FVector NoiseSpot() const { return LastSeen; }
	bool IsHeld() const { return HoldT > 0.0f; }
	bool IsBusy() const { return bRepairing || bWaitBuddy || bEscort || BodyTarget != nullptr; }
	void DarkChecked() { bDarkChecked = true; }
	/** Se planta y espera a B (o Seconds, lo que llegue antes); B deja lo suyo y acude. Sin B, duda ese rato y entra solo. */
	void WaitForBuddy(ATarsisGuard* B, float Seconds);
	/** La linterna (para medir la luz desde fuera de la clase); nullptr si aún no la ha sacado nunca. */
	const class USpotLightComponent* FlashlightComp() const { return Flashlight; }
	void SetFlashlightShadows(bool bOn);

	/** Arreglando el generador: se queda junto a él barriendo la zona con la linterna (si te ve, deja de arreglar). */
	void StartRepair(const FVector& Center);
	void StopRepair();
	bool IsRepairing() const { return bRepairing; }
	/** Tanda 40 (los pone el director cada tick): la caja de carton (0 = nadie te ve) y el uniforme (mas lejos de
	GFarLimit cm no te distinguen de un guardia; 0 = sin uniforme). */
	static float GSeenMul;
	/** Tanda 44: a menos de esto (cm), de frente, la caja de carton ya no engana. */
	static float GBoxNear;
	static float GFarLimit;
	/** Tanda 45: preso tras la reja cerrada. Nadie da la voz por ver a un preso en su celda. */
	static bool GPrisoner;

	/** Dormido con un dardo: se le puede quitar (E) y vuelve a la pistola. */
	bool bDarted = false;

	/** En alerta porque se lo han mandado por radio (no te ha visto): no abandona por UnseenT antes de llegar. */
	bool bRadioCall = false;

protected:
	virtual void BeginPlay() override;
	virtual void OnConstruction(const FTransform& Transform) override;

	UPROPERTY(VisibleAnywhere, Category = "Tarsis")
	TObjectPtr<UStaticMeshComponent> Body;

	UPROPERTY(VisibleAnywhere, Category = "Tarsis")
	TObjectPtr<UStaticMeshComponent> Head;

	UPROPERTY(VisibleAnywhere, Category = "Tarsis")
	TObjectPtr<UTextRenderComponent> Mark;

	UPROPERTY()
	TObjectPtr<class USpotLightComponent> Flashlight;

	UPROPERTY()
	TObjectPtr<UStaticMeshComponent> Baton;

	UPROPERTY()
	TObjectPtr<class UPointLightComponent> BatonGlow;

	/** Cuerpo que se ve en el juego: copia la pose de la malla animada (oculta) y le añade el giro de cabeza y cuello y
	 *  la inclinación al buscar. Con SingleNode no hay grafo de animación donde meter un LookAt. */
	UPROPERTY()
	TObjectPtr<class UPoseableMeshComponent> Pose;

private:
	float StunT = 0.0f;
	UPROPERTY()
	TObjectPtr<ATarsisGuard> BodyTarget;
	void BodyTick(float DeltaSeconds, APawn* Player, float V);
	void SetupPose();
	void LookTick(float DeltaSeconds);
	void FootTick(float DeltaSeconds);
	void GestureTick(float DeltaSeconds);
	void BatonTick(float DeltaSeconds);
	float BatonLeft = 0.0f;
	void AimBone(FName Bone, FName Child, const FVector& DirCS, float W);
	FName ArmBones[2][3];      // [derecho, izquierdo][brazo, antebrazo, mano]
	FName Gesture;
	float GestureLeft = 0.0f;
	float GestureT = 0.0f;
	FVector GestureDir = FVector::ZeroVector;
	float ArmW[2] = { 0.0f, 0.0f };      // peso del gesto en cada brazo
	FVector ArmDir[2][2];                // dirección suavizada de brazo y antebrazo, en ejes del guardia
	float GestureHead = 0.0f;
	float GestureLean = 0.0f;
	void StopGesture();
	float LookTarget = 0.0f;
	float Lean = 0.0f;
	float PrevYaw = 0.0f;
	float YawRate = 0.0f;
	float FootMin[2] = { 0.0f, 0.0f };
	bool bFootUp[2] = { true, true };
	bool bFootInit = false;
	/** Fue a mirar un ruido (para la frase al volver: «habrá sido el viento»). */
	bool bNoiseSearch = false;
	FName HeadBone, NeckBone, SpineBone;
	int32 PointIndex = 0;
	float WaitT = 0.0f;
	float StateT = 0.0f;
	float UnseenT = 0.0f;
	FVector LastSeen = FVector::ZeroVector;
	FVector Home = FVector::ZeroVector;
	FVector MoveDest = FVector(1e9f);
	bool bNoPath = false;
	float DownT = 0.0f;
	bool bInvestigate = false;
	bool bShadow = false;
	FVector ShadowFrom = FVector::ZeroVector;
	float ShadowHoldT = 0.0f;
	float BlendPos = 0.0f;
	bool bRepairing = false;
	FVector RepairCenter = FVector::ZeroVector;
	float SweepT = 0.0f;
	float RepairLookT = 0.0f;
	float LastRepairNoise = -100.0f;
	FVector RepairLook = FVector::ZeroVector;
	float HoldT = 0.0f;
	bool bErrand = false;
	bool bErrandThere = false;
	FVector ErrandLoc = FVector::ZeroVector;
	FVector ErrandFace = FVector::ZeroVector;
	float ErrandT = 0.0f;
	void WakeUp();
	/** Tanda 45: lo levantan los suyos y vuelve a su puesto sin buscar a nadie (al capturarte). */
	void Recover();
	void LookForBodies();

	void SetState(ETarsisGuardState NewState);
	void Walk(const FVector& Dest, float Speed);
	void FaceTowards(const FVector& Dest, float DeltaSeconds);
	bool Near2D(const FVector& Dest, float Radius) const;
	void Caught(APawn* Player);
	void UpdateMark();
	void SetupBody();
	void UpdateAnim();
	void TowerTick(float DeltaSeconds, APawn* Player, float V);
	// tanda 37 (TarsisCombat.cpp): armado y con cabeza
	bool ArmedTick(float DeltaSeconds, APawn* Player, float V);
	bool FindCover(const FVector& Threat, FVector& Out) const;
	void FireAt(APawn* Player, float Dist, float V, class ATarsisDirector* D);
	void TowerShootTick(float DeltaSeconds, APawn* Player, float V);
	float TowerAimT = 0.0f;
	FVector CoverThreat = FVector::ZeroVector;
	float AimT = 0.0f;
	float ShotT = 0.0f;
	float CoverT = 0.0f;
	float TowerT = 0.0f;
	float LightPitch = 0.0f;
	TWeakObjectPtr<ATarsisGuard> Buddy;
	float WaitBuddyT = 0.0f;
	bool bDarkChecked = false;
	bool bEscort = false;      // acude a acompañar a otro: no vuelve a pedir apoyo él
	void AutoTorchTick(float DeltaSeconds);
	void ShowTorch(bool bOn);
	float DazzleCoolT = 0.0f;
	bool bDazzled = false;
	bool bAutoTorch = false;   // encendida por estar a oscuras: se guarda al volver a la luz
	float TorchT = 0.0f;
	int32 TorchLit = 0;
	float TorchOnFor = 0.0f;
	UPROPERTY() TObjectPtr<class UStaticMeshComponent> TorchLens;
	UPROPERTY() TObjectPtr<class UStaticMeshComponent> TorchGlow;
	bool bDarkTorch = false;   // linterna sacada para entrar a oscuras: se guarda al volver a la ronda
	bool HasSweepPath() const { return SweepPath.Num() >= 2 && TowerLight != nullptr; }
	void SweepSequence(TArray<int32>& Out) const;
	float SweepTimeNear(const FVector& P) const;
	void AimBeam(float DeltaSeconds, bool bSnap);
	FVector BeamCall = FVector::ZeroVector;
	bool bSweepAway = false;
	float BeamPaint = 0.0f;
	TObjectPtr<UAnimationAsset> CurrentAnim;
	// tanda A: animación de Epic
	UPROPERTY() TObjectPtr<USkeletalMeshComponent> GaspBody;
	UPROPERTY() TObjectPtr<UClass> GaspRetargetClass;
	bool bGaspSingle = false;      // el cuerpo hace una animación suelta (caer, apuntar) en vez del retarget
	FString GaspGaitNow;
	FTarsisGaspTurn GaspTurn;
	bool SetupGasp();
	void GaspFindRetargeter();
	void GaspPointRetargeter();
	void GaspSingle(UAnimationAsset* A, bool bLoop);
	void GaspRestore();
	bool GaspSetEnum(FName Prop, const FString& Value);
	bool GaspTick();   // true si el guardia anima con el GASP (UpdateAnim no hace nada más)
};
