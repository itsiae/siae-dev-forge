/**
 * JUNIT5 + MOCKITO + ASSERTJ TEMPLATE — Java 7/8 compatibility (Task 07)
 * ====================================================================
 * Variante per repo SIAE legacy con <source>1.7</source> o <source>1.8</source>.
 * NO `var` keyword (Java 10+). NO text-blocks (Java 15+). NO switch-expr/record.
 * Lo placeholder {{TypeXxx}} è da sostituire con il tipo esplicito durante
 * generation Phase 5.
 *
 * @Mock crea un mock vuoto. @InjectMocks costruisce il SUT iniettando i @Mock.
 * when(mock.method(...)).thenReturn(...) configura il behavior.
 * verify(mock).method(...) asserisce l'invocazione.
 * ====================================================================
 *
 * Use this template for: Spring Boot 1.x/2.x, Java 7/8 SIAE legacy.
 * Requires: JUnit 5 (junit-jupiter), Mockito 5+, AssertJ, JaCoCo.
 * Replace all {{PLACEHOLDER}} tokens before use, including {{TypeXxx}}.
 */

package {{package_name}};

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.NullAndEmptySource;
import org.junit.jupiter.params.provider.ValueSource;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

import {{full_class_import}};
import {{full_dep_import}};

@ExtendWith(MockitoExtension.class)
@DisplayName("{{ClassName}} unit tests")
class {{ClassName}}Test {

    @Mock
    private {{DepInterface}} {{depName}};

    @InjectMocks
    private {{ClassName}} {{instanceName}};

    // ─── Happy Path ───────────────────────────────────────────────────────────

    @Test
    @DisplayName("should {{HAPPY_PATH_DESCRIPTION}}")
    void should{{HappyPathMethodName}}() {
        // Arrange (Java 8 — explicit types, no var)
        {{TypeInput}} input = {{HAPPY_PATH_INPUT}};
        {{TypeExpected}} expected = {{EXPECTED_OUTPUT}};
        when({{depName}}.{{depMethod}}(any())).thenReturn({{DEP_RETURN_VALUE}});

        // Act
        {{TypeResult}} result = {{instanceName}}.{{methodName}}(input);

        // Assert
        assertThat(result).isEqualTo(expected);
        verify({{depName}}).{{depMethod}}(input);
        verifyNoMoreInteractions({{depName}});
    }

    // ─── Edge Cases ───────────────────────────────────────────────────────────

    @Test
    @DisplayName("should {{EDGE_CASE_1_DESCRIPTION}} when input is empty")
    void should{{EdgeCase1MethodName}}WhenInputIsEmpty() {
        // Arrange
        {{TypeInput}} emptyInput = {{EDGE_CASE_1_INPUT}};
        when({{depName}}.{{depMethod}}(any())).thenReturn({{EDGE_CASE_1_DEP_RETURN}});

        // Act
        {{TypeResult}} result = {{instanceName}}.{{methodName}}(emptyInput);

        // Assert
        assertThat(result).isEqualTo({{EDGE_CASE_1_EXPECTED}});
    }

    @ParameterizedTest
    @ValueSource(strings = { {{EDGE_CASE_2_VALUES}} })
    @DisplayName("should {{EDGE_CASE_2_DESCRIPTION}} for boundary values")
    void should{{EdgeCase2MethodName}}ForBoundaryValues(String boundaryInput) {
        // Arrange
        when({{depName}}.{{depMethod}}(any())).thenReturn({{EDGE_CASE_2_DEP_RETURN}});

        // Act
        {{TypeResult}} result = {{instanceName}}.{{methodName}}(boundaryInput);

        // Assert
        assertThat(result).isNotNull();
    }

    // ─── Negative Path ────────────────────────────────────────────────────────

    @Test
    @DisplayName("should throw {{ExceptionType}} when {{NEGATIVE_CONDITION}}")
    void shouldThrow{{ExceptionType}}When{{NegativeConditionName}}() {
        // Arrange
        {{TypeInput}} invalidInput = {{INVALID_INPUT}};
        when({{depName}}.{{depMethod}}(any()))
            .thenThrow(new {{ExceptionType}}("{{ERROR_MESSAGE}}"));

        // Act & Assert
        assertThatThrownBy(() -> {{instanceName}}.{{methodName}}(invalidInput))
            .isInstanceOf({{ExceptionType}}.class)
            .hasMessageContaining("{{ERROR_MESSAGE}}");
    }

    @ParameterizedTest
    @NullAndEmptySource
    @DisplayName("should throw when input is null or empty")
    void shouldThrowWhenInputIsNullOrEmpty(String nullOrEmpty) {
        assertThatThrownBy(() -> {{instanceName}}.{{methodName}}(nullOrEmpty))
            .isInstanceOf(IllegalArgumentException.class);
    }
}
