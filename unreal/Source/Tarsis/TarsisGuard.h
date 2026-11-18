// Lost Horizon: De Profundis — núcleo del sigilo (fase 2 del plan de migración).
// Guardia de la base de Tarsis: ronda por puntos, vista con cono, distancia y luz, «?» y «!», alerta y captura.
// Se copia en Source/<Módulo>/Tarsis/ del proyecto de Unreal (ver unreal/README.md).
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
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
};
