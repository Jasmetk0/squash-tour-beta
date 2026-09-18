            if self.qualification_sections:
                raise ValueError("Historical Draw authority v1 cannot contain Qualification sections")
        else:
            if self.qualification is not None:
                raise ValueError("Draw authority v2 uses Qualification sections, not the v1 bracket")
            expected_section_ids = tuple(
                f"Q{index}" for index in range(1, len(self.qualification_sections) + 1)
            )
            actual_section_ids = tuple(section.section_id for section in self.qualification_sections)
            if actual_section_ids != expected_section_ids:
                raise ValueError("Qualification section identities must be canonical Q1..Qn")
        return self

    @property
    def qualification_brackets(self) -> tuple[TournamentDrawBracket, ...]:
        if self.qualification_sections:
            return self.qualification_sections
        return (self.qualification,) if self.qualification is not None else ()

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


class TournamentDrawAuthorityBuilder:
    """Generate replayable brackets only from immutable Draw Input authority."""

    @classmethod
    def build(
        cls,
        *,
        draw_input: TournamentDrawInputAuthority,
        command_id: str,
        algorithm_version: TournamentDrawAlgorithmVersion = "idealized_seed_tiers.v2",
    ) -> TournamentDrawAuthority:
        capacity = draw_input.capacity
        if capacity.wild_card_slots:
            raise ValueError(
                "Tournament Draw authority requires Wild Card resolution before generation"
            )
        if capacity.main_draw_size < 2 or not _is_power_of_two(capacity.main_draw_size):
            raise ValueError(
                "Canonical Run-owned Main Draw currently supports complete binary brackets"
            )
        if capacity.qualification_draw_size == 0 and capacity.qualifier_spots != 0:
            raise ValueError(
                "Qualification slots require a non-empty Qualification Draw"
            )
        if capacity.qualification_draw_size > 0 and capacity.qualifier_spots <= 0:
            raise ValueError(
                "Qualification Draw requires at least one qualifier spot"
            )
        if capacity.qualification_draw_size == 1:
            raise ValueError(
                "One-position Qualification Draw requires an explicit auto-qualification policy"
            )
        if capacity.qualifier_spots > 0:
            if capacity.qualification_draw_size % capacity.qualifier_spots:
                raise ValueError(
                    "Qualification field must split evenly across equal Q sections"
                )
            qualification_section_size = (
                capacity.qualification_draw_size // capacity.qualifier_spots
            )
            if qualification_section_size < 2 or not _is_power_of_two(
                qualification_section_size
            ):
                raise ValueError(
                    "Each canonical Qualification section must be a complete binary bracket"
                )

        if algorithm_version == "idealized_seed_tiers.v2":
            expected_main_seed_count = _master_seed_count(
                bracket_size=capacity.main_draw_size,
                actual_player_count=len(draw_input.direct_main_player_ids),
            )
            if draw_input.main_seed_count != expected_main_seed_count:
                raise ValueError(
                    "Main seed count differs from the Master bracket seed formula"
                )
            if capacity.qualification_draw_size and capacity.qualifier_spots == 1:
                expected_q_seed_count = _master_seed_count(
                    bracket_size=capacity.qualification_draw_size,
                    actual_player_count=len(draw_input.qualification_player_ids),
                )
                if draw_input.qualification_seed_count != expected_q_seed_count:
                    raise ValueError(
                        "Qualification seed count differs from the Master bracket seed formula"
                    )

        expected_main_occupants = (
            len(draw_input.direct_main_player_ids)
            + len(draw_input.qualifier_placeholder_ids)
            + capacity.bye_slots
        )
        if expected_main_occupants != capacity.main_draw_size:
            raise ValueError(
                "Canonical Run-owned Main Draw requires a fully resolved field including explicit BYEs"
            )
        if len(draw_input.qualification_player_ids) > capacity.qualification_draw_size:
            raise ValueError(
                "Canonical Run-owned Qualification field exceeds configured capacity"
            )
        qualification_bye_count = (
            capacity.qualification_draw_size
            - len(draw_input.qualification_player_ids)
        )

        qualification = None
        qualification_sections: tuple[TournamentDrawBracket, ...] = ()
        if capacity.qualification_draw_size:
            if capacity.qualifier_spots == 1:
                qualification = cls._build_bracket(
                    draw_input=draw_input,
                    draw_type="qualification",
                    bracket_size=capacity.qualification_draw_size,
                    player_ids=draw_input.qualification_player_ids,
                    seed_player_ids=draw_input.qualification_seed_player_ids,
                    placeholder_ids=(),
                    explicit_byes=qualification_bye_count,
                    algorithm_version=algorithm_version,
                )
            else:
                qualification_sections = cls._build_qualification_sections(
                    draw_input=draw_input,
                    algorithm_version=algorithm_version,
                )

        main = cls._build_bracket(
            draw_input=draw_input,
            draw_type="main",
            bracket_size=capacity.main_draw_size,
            player_ids=draw_input.direct_main_player_ids,
            seed_player_ids=draw_input.main_seed_player_ids,
            placeholder_ids=draw_input.qualifier_placeholder_ids,
            explicit_byes=capacity.bye_slots,
            algorithm_version=algorithm_version,
        )
        return TournamentDrawAuthority(
            schema_version=(
                "tournament_draw_authority.v2"
                if qualification_sections
                else "tournament_draw_authority.v1"
            ),
            algorithm_version=algorithm_version,
            run_id=draw_input.run_id,
            branch_id=draw_input.branch_id,
            event_id=draw_input.event_id,
            generated_by_command_id=command_id,
            draw_input_fingerprint=draw_input.fingerprint,
            qualification=qualification,
            qualification_sections=qualification_sections,
            main=main,
        )

    @classmethod
    def _build_qualification_sections(
        cls,
        *,
        draw_input: TournamentDrawInputAuthority,
        algorithm_version: TournamentDrawAlgorithmVersion,
    ) -> tuple[TournamentDrawBracket, ...]:
        capacity = draw_input.capacity
        section_count = capacity.qualifier_spots
        section_size = capacity.qualification_draw_size // section_count
        total_byes = (
            capacity.qualification_draw_size
            - len(draw_input.qualification_player_ids)
        )
        bye_counts = _qualification_byes_by_section(
            section_count=section_count,
            section_size=section_size,
            total_byes=total_byes,
            draw_seed=draw_input.draw_seed,
            event_id=draw_input.event_id,
        )

        expected_seed_count = _master_qualification_seed_count(
            section_count=section_count,
            section_size=section_size,
            actual_player_count=len(draw_input.qualification_player_ids),
        )
        if draw_input.qualification_seed_count != expected_seed_count:
            raise ValueError(
                "Qualification seed count must match the Master seed formula across Q sections"
            )

        global_seeds = draw_input.qualification_seed_player_ids
        section_seeds: list[list[tuple[int, str]]] = [
            [] for _ in range(section_count)
        ]

        seed_cursor = 0
        layer = 0
        while seed_cursor < len(global_seeds):
            layer += 1
            layer_players = list(
                global_seeds[seed_cursor : seed_cursor + section_count]
            )
            section_order = list(range(section_count))
            if layer > 1:
                rng = DeterministicRng(
                    _draw_named_subseed(
                        draw_seed=draw_input.draw_seed,
                        event_id=draw_input.event_id,
                        key=f"qualification:seed-layer:{layer}",
                    )
                )
                rng.shuffle(section_order)
            for offset, player_id in enumerate(layer_players):
                section_index = section_order[offset]
                global_seed_number = seed_cursor + offset + 1
                section_seeds[section_index].append(
                    (global_seed_number, player_id)
                )
            seed_cursor += len(layer_players)

        unseeded = list(
            draw_input.qualification_player_ids[draw_input.qualification_seed_count :]
        )
        unseeded_rng = DeterministicRng(
            _draw_named_subseed(
                draw_seed=draw_input.draw_seed,
                event_id=draw_input.event_id,
                key="qualification:unseeded-distribution",
            )
        )
        unseeded_rng.shuffle(unseeded)

        sections = []
        cursor = 0
        for section_index in range(section_count):
            section_id = f"Q{section_index + 1}"
            seed_pairs = tuple(section_seeds[section_index])
            seeds = tuple(player_id for _, player_id in seed_pairs)
            seed_numbers = tuple(number for number, _ in seed_pairs)
            available_player_slots = (
                section_size
                - bye_counts[section_index]
                - len(seeds)
            )
            if available_player_slots < 0:
                raise ValueError(
                    "Qualification BYE layering conflicts with protected seed capacity"
                )
            extras = tuple(
                unseeded[cursor : cursor + available_player_slots]
            )
            cursor += available_player_slots
            sections.append(
                cls._build_bracket(
                    draw_input=draw_input,
                    draw_type="qualification",
                    bracket_size=section_size,
                    player_ids=(*seeds, *extras),
                    seed_player_ids=seeds,
                    seed_numbers=seed_numbers,
                    placeholder_ids=(),
                    explicit_byes=bye_counts[section_index],
                    section_id=section_id,
                    section_ordinal=section_index,
                    section_count=section_count,
                    algorithm_version=algorithm_version,
                )
            )
        if cursor != len(unseeded):
            raise ValueError(
                "Qualification player distribution did not fill all non-BYE Q slots exactly"
            )
        return tuple(sections)

    @classmethod
    def _build_bracket(
        cls,
        *,
        draw_input: TournamentDrawInputAuthority,
        draw_type: TournamentDrawType,
        bracket_size: int,
        player_ids: tuple[str, ...],
        seed_player_ids: tuple[str, ...],
        seed_numbers: tuple[int, ...] | None = None,
        placeholder_ids: tuple[str, ...],
        explicit_byes: int,
        section_id: str | None = None,
        section_ordinal: int = 0,
        section_count: int = 1,
        algorithm_version: TournamentDrawAlgorithmVersion,
    ) -> TournamentDrawBracket:
        if len(set(player_ids)) != len(player_ids):
            raise ValueError("Tournament draw contains duplicate player identities")
        if tuple(player_ids[: len(seed_player_ids)]) != seed_player_ids:
            raise ValueError(
                "Tournament draw seeds must follow the frozen ranking-derived field order"
            )

        effective_seed_numbers = (
            seed_numbers
            if seed_numbers is not None
            else tuple(range(1, len(seed_player_ids) + 1))
        )
        if len(effective_seed_numbers) != len(seed_player_ids):
            raise ValueError("Tournament draw seed identity count differs from seed players")
        if len(set(effective_seed_numbers)) != len(effective_seed_numbers):
            raise ValueError("Tournament draw seed identities must be unique")

        draw_scope = draw_type if section_id is None else f"{draw_type}:{section_id}"
        idealized_by_position = (
            _idealized_slot_order(bracket_size)
            if algorithm_version == "idealized_seed_tiers.v2"
            else ()
        )
        local_seed_positions = (
            _master_seed_positions(
                bracket_size=bracket_size,
                seed_count=len(seed_player_ids),
                draw_seed=draw_input.draw_seed,
                event_id=draw_input.event_id,
                draw_scope=draw_scope,
            )
            if algorithm_version == "idealized_seed_tiers.v2"
            else _seed_positions(bracket_size, len(seed_player_ids))
        )

        seed_positions: dict[int, int] = {}
        slots: dict[int, TournamentDrawSlot | None] = {
            index: None for index in range(1, bracket_size + 1)
        }
        for local_seed_number, (seed_number, player_id) in enumerate(
            zip(effective_seed_numbers, seed_player_ids, strict=True),
            start=1,
        ):
            position = local_seed_positions[local_seed_number]
            seed_positions[seed_number] = position
            slots[position] = TournamentDrawSlot(
                slot_index=position,
                idealized_slot_number=(
                    idealized_by_position[position - 1]
                    if idealized_by_position
                    else None
                ),
                entrant_kind="player",
                player_id=player_id,
                seed_number=seed_number,
                is_seed_protected=True,
            )

        bye_positions = (
            _choose_master_bye_positions(
                bracket_size=bracket_size,
                explicit_byes=explicit_byes,
                occupied_positions={
                    index for index, slot in slots.items() if slot is not None
                },
            )
            if algorithm_version == "idealized_seed_tiers.v2"
            else _choose_bye_positions(
                bracket_size=bracket_size,
                explicit_byes=explicit_byes,
                seed_positions=seed_positions,
                occupied_positions={
                    index for index, slot in slots.items() if slot is not None
                },
            )
        )
        for position in bye_positions:
            slots[position] = TournamentDrawSlot(
                slot_index=position,
                idealized_slot_number=(
                    idealized_by_position[position - 1]
                    if idealized_by_position
                    else None
                ),
                entrant_kind="bye",
            )

        open_positions = [
            index for index in range(1, bracket_size + 1) if slots[index] is None
        ]
        rng = DeterministicRng(
            _draw_subseed(
                draw_seed=draw_input.draw_seed,
                event_id=draw_input.event_id,
                draw_type=(
                    draw_type if section_id is None else f"{draw_type}:{section_id}"
                ),
            )
        )
        rng.shuffle(open_positions)

        remaining_players = player_ids[len(seed_player_ids) :]
        entrants: tuple[tuple[str, str], ...] = tuple(
            ("player", player_id) for player_id in remaining_players
        ) + tuple(("qualifier_placeholder", value) for value in placeholder_ids)
        if len(entrants) != len(open_positions):
            raise ValueError(
                "Tournament draw entrant count differs from available bracket positions"
            )

        for position, (kind, identity) in zip(open_positions, entrants, strict=True):
            if kind == "player":
                slots[position] = TournamentDrawSlot(
                    slot_index=position,
                    idealized_slot_number=(
                        idealized_by_position[position - 1]
                        if idealized_by_position
                        else None
                    ),
                    entrant_kind="player",
                    player_id=identity,
                )
            else:
                slots[position] = TournamentDrawSlot(
                    slot_index=position,
                    idealized_slot_number=(
                        idealized_by_position[position - 1]
                        if idealized_by_position
                        else None
                    ),
                    entrant_kind="qualifier_placeholder",
                    placeholder_id=identity,
                )

        final_slots = tuple(slots[index] for index in range(1, bracket_size + 1))
        if any(slot is None for slot in final_slots):
            raise ValueError("Tournament draw generation left unresolved bracket slots")
        typed_slots = tuple(slot for slot in final_slots if slot is not None)
        qualifier_slots = tuple(
            (slot.placeholder_id, slot.slot_index)
            for slot in typed_slots
            if slot.entrant_kind == "qualifier_placeholder"
            and slot.placeholder_id is not None
        )
        return TournamentDrawBracket(
            draw_type=draw_type,
            section_id=section_id,
            bracket_size=bracket_size,
            seed_positions=tuple(sorted(seed_positions.items())),
            slots=typed_slots,
            nodes=_build_nodes(
                draw_input.event_id,
                draw_type,
                bracket_size,
                section_id=section_id,
                section_ordinal=section_ordinal,
                section_count=section_count,
            ),
            bye_slot_indexes=tuple(
                slot.slot_index for slot in typed_slots if slot.entrant_kind == "bye"
            ),
            qualifier_placeholder_slots=qualifier_slots,
        )


def _master_seed_count(*, bracket_size: int, actual_player_count: int) -> int:
    if actual_player_count < 0:
        raise ValueError("Actual player count cannot be negative")
    if actual_player_count == 0:
        return 0
    return min(actual_player_count, max(1, bracket_size // 4))


def _idealized_slot_order(bracket_size: int) -> tuple[int, ...]:
    if bracket_size < 2 or not _is_power_of_two(bracket_size):
        raise ValueError("Tournament bracket size must be a power of two >= 2")
    order = [1]
    size = 1
    while size < bracket_size:
        next_size = size * 2
        expanded: list[int] = []
        for index, value in enumerate(order):
            pair = (value, next_size + 1 - value)
            expanded.extend(pair if index % 2 == 0 else reversed(pair))
        order = expanded
        size = next_size
    return tuple(order)


def _master_seed_positions(
    *,
    bracket_size: int,
    seed_count: int,
    draw_seed: int,
    event_id: str,
    draw_scope: str,
) -> dict[int, int]:
    if seed_count < 0 or seed_count > bracket_size:
        raise ValueError("Tournament draw seed count exceeds bracket size")
    if seed_count == 0:
        return {}
    idealized_by_position = _idealized_slot_order(bracket_size)
    physical_by_idealized = {
        idealized: position
        for position, idealized in enumerate(idealized_by_position, start=1)
    }
    assigned_idealized: dict[int, int] = {1: 1}
    if seed_count >= 2:
        assigned_idealized[2] = 2
    tier_start = 3
    while tier_start <= seed_count:
        tier_capacity_end = min(bracket_size, 2 * (tier_start - 1))
        actual_seed_end = min(seed_count, tier_capacity_end)
        idealized_slots = list(range(tier_start, tier_capacity_end + 1))
        rng = DeterministicRng(
            _draw_named_subseed(
                draw_seed=draw_seed,
                event_id=event_id,
                key=(
                    f"{draw_scope}:seed-tier:"
                    f"{tier_start}-{tier_capacity_end}"
                ),
            )
        )
        rng.shuffle(idealized_slots)
        actual_seed_numbers = list(range(tier_start, actual_seed_end + 1))
        for seed_number, idealized_slot in zip(
            actual_seed_numbers,
            idealized_slots[: len(actual_seed_numbers)],
            strict=True,
        ):
            assigned_idealized[seed_number] = idealized_slot
        tier_start = tier_capacity_end + 1
    return {
        seed_number: physical_by_idealized[idealized_slot]
        for seed_number, idealized_slot in assigned_idealized.items()
    }


def _choose_master_bye_positions(
    *,
    bracket_size: int,
    explicit_byes: int,
    occupied_positions: set[int],
) -> tuple[int, ...]:
    if explicit_byes < 0:
        raise ValueError("Tournament draw BYE count cannot be negative")
    idealized_by_position = _idealized_slot_order(bracket_size)
    physical_by_idealized = {
        idealized: position
        for position, idealized in enumerate(idealized_by_position, start=1)
    }
    positions = []
    for idealized_slot in range(
        bracket_size, bracket_size - explicit_byes, -1
    ):
        position = physical_by_idealized[idealized_slot]
        if position in occupied_positions:
            raise ValueError(
                "Master BYE idealized slot conflicts with a protected seed position"
            )
        positions.append(position)
    return tuple(sorted(positions))


def _master_qualification_seed_count(
    *,
    section_count: int,
    section_size: int,
    actual_player_count: int,
) -> int:
    if actual_player_count < 0:
        raise ValueError("Actual Qualification player count cannot be negative")
    maximum_seed_pool = section_count * max(1, section_size // 4)
    return min(actual_player_count, maximum_seed_pool)


def _qualification_byes_by_section(
    *,
    section_count: int,
    section_size: int,
    total_byes: int,
    draw_seed: int,
    event_id: str,
) -> tuple[int, ...]:
    if total_byes < 0 or total_byes > section_count * section_size:
        raise ValueError("Qualification BYE count is outside configured capacity")
    full_layers, remainder = divmod(total_byes, section_count)
    if full_layers > section_size:
        raise ValueError("Qualification BYE layers exceed section capacity")

    counts = [full_layers for _ in range(section_count)]
    if remainder:
        section_order = list(range(section_count))
        rng = DeterministicRng(
            _draw_named_subseed(
                draw_seed=draw_seed,
                event_id=event_id,
                key=(
                    "qualification:bye-layer:"
                    f"{full_layers + 1}"
                ),
            )
        )
        rng.shuffle(section_order)
        for section_index in section_order[:remainder]:
            counts[section_index] += 1
    return tuple(counts)


def _draw_subseed(
    *, draw_seed: int, event_id: str, draw_type: str
) -> int:
    material = (
        f"tournament_draw_authority.v1|{draw_seed}|{event_id}|{draw_type}"
    ).encode()
    return int.from_bytes(
        hashlib.blake2b(material, digest_size=16).digest(),
        byteorder="big",
        signed=False,
    )


def _draw_named_subseed(*, draw_seed: int, event_id: str, key: str) -> int:
    return _draw_subseed(draw_seed=draw_seed, event_id=event_id, draw_type=key)


def _is_power_of_two(value: int) -> bool:
    return value > 0 and (value & (value - 1)) == 0


def _paired_slot(slot_index: int) -> int:
    return slot_index + 1 if slot_index % 2 else slot_index - 1


def _choose_bye_positions(
    *,
    bracket_size: int,
    explicit_byes: int,
    seed_positions: dict[int, int],
    occupied_positions: set[int],
) -> tuple[int, ...]:
    if explicit_byes < 0:
        raise ValueError("Tournament draw BYE count cannot be negative")
    bye_positions: list[int] = []
    for seed_number in sorted(seed_positions):
        if len(bye_positions) >= explicit_byes:
            break
        opponent = _paired_slot(seed_positions[seed_number])
        if opponent not in occupied_positions and opponent not in bye_positions:
            bye_positions.append(opponent)
    for position in range(1, bracket_size + 1):
        if len(bye_positions) >= explicit_byes:
            break
        if position not in occupied_positions and position not in bye_positions:
            bye_positions.append(position)
    if len(bye_positions) != explicit_byes:
        raise ValueError("Tournament draw cannot place all explicit BYEs")
    return tuple(sorted(bye_positions))


def _seed_positions(bracket_size: int, seeds_count: int) -> dict[int, int]:
    if seeds_count < 0 or seeds_count > bracket_size:
        raise ValueError("Tournament draw seed count exceeds bracket size")
    if not seeds_count:
        return {}
    placement_order = _seed_placement_order(bracket_size)
    return {
        seed_number: placement_order[seed_number - 1]
        for seed_number in range(1, seeds_count + 1)
    }