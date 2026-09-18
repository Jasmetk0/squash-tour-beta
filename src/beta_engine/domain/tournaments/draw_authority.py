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
        if (
            capacity.qualifier_spots > 0
            and len(draw_input.qualification_player_ids) < capacity.qualifier_spots
        ):
            raise ValueError(
                "Qualification requires at least one real player per Q section"
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