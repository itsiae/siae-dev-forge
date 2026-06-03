/**
 * JUNIT5 + MOCKITO TEMPLATE — Mock pattern rationale
 * ====================================================================
 * @Mock crea un mock vuoto (default behavior: null/0/false).
 * @InjectMocks costruisce il SUT iniettando i @Mock nel constructor (preferito) o setter.
 * when(mock.method(...)).thenReturn(...) configura il behavior.
 * verify(mock).method(...) asserisce l'invocazione.
 * Per static methods: usa Mockito.mockStatic() in try-with-resources.
 * ====================================================================
 *
 * Use this template for: Spring Boot, Quarkus, Micronaut, or plain Java 17+.
 * Requires: JUnit 5 (junit-jupiter), Mockito 5+, AssertJ, JaCoCo.
 * Replace all {{PLACEHOLDER}} tokens before use.
 *
 * C1 fix — Placeholder cleanup (HIGH severity)
 * ====================================================================
 * Java import lines (`import com.example.Foo;`) sono FQN single-symbol —
 * non hanno il problema di list trailing comma. Tuttavia, se
 * {{full_dep_import}} resta vuoto post-sostituzione, produce `import ;`
 * SyntaxError. `clean_template_placeholders` rileva riga
 * `import\s*;` e la rimuove (idempotente).
 * ====================================================================
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
        // Arrange
        var input = {{HAPPY_PATH_INPUT}};
        var expected = {{EXPECTED_OUTPUT}};
        when({{depName}}.{{depMethod}}(any())).thenReturn({{DEP_RETURN_VALUE}});

        // Act
        var result = {{instanceName}}.{{methodName}}(input);

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
        var emptyInput = {{EDGE_CASE_1_INPUT}};
        when({{depName}}.{{depMethod}}(any())).thenReturn({{EDGE_CASE_1_DEP_RETURN}});

        // Act
        var result = {{instanceName}}.{{methodName}}(emptyInput);

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
        var result = {{instanceName}}.{{methodName}}(boundaryInput);

        // Assert
        assertThat(result).isNotNull();
    }

    // ─── Negative Path ────────────────────────────────────────────────────────

    @Test
    @DisplayName("should throw {{ExceptionType}} when {{NEGATIVE_CONDITION}}")
    void shouldThrow{{ExceptionType}}When{{NegativeConditionName}}() {
        // Arrange
        var invalidInput = {{INVALID_INPUT}};
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

    // ─── Nested Group (optional — use for complex classes with multiple methods)

    @Nested
    @DisplayName("{{secondMethodName}}")
    class {{SecondMethodName}}Tests {

        @Test
        @DisplayName("should {{SECOND_HAPPY_PATH_DESCRIPTION}}")
        void shouldReturnExpectedResult() {
            // Arrange
            var input = {{SECOND_HAPPY_PATH_INPUT}};
            // Act
            var result = {{instanceName}}.{{secondMethodName}}(input);
            // Assert
            assertThat(result).isNotNull();
        }

        @Test
        @DisplayName("should throw when dependency is unavailable")
        void shouldThrowWhenDependencyFails() {
            // Arrange
            doThrow(new RuntimeException("unavailable"))
                .when({{depName}}).{{depMethod}}(any());

            // Act & Assert
            assertThatThrownBy(() -> {{instanceName}}.{{secondMethodName}}({{SECOND_HAPPY_PATH_INPUT}}))
                .isInstanceOf({{ServiceExceptionType}}.class);
        }
    }
}
