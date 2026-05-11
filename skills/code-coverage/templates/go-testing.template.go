// Use this template for: Go services (Gin, Echo, Fiber, Chi, plain net/http).
// Requires: go test (stdlib), github.com/stretchr/testify.
// Replace all {{PLACEHOLDER}} tokens before use.

package {{package_name}}_test

import (
	"context"
	"errors"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
	"github.com/stretchr/testify/require"

	"{{module_path}}/{{package_name}}"
)

// ─── Mock for {{DepInterface}} ────────────────────────────────────────────────

type Mock{{DepInterface}} struct {
	mock.Mock
}

func (m *Mock{{DepInterface}}) {{DepMethod}}(ctx context.Context, input {{InputType}}) ({{ReturnType}}, error) {
	args := m.Called(ctx, input)
	return args.Get(0).({{ReturnType}}), args.Error(1)
}

// ─── Tests for {{FunctionName}} ───────────────────────────────────────────────

func Test{{FunctionName}}(t *testing.T) {
	t.Run("happy path — {{HAPPY_PATH_DESCRIPTION}}", func(t *testing.T) {
		// Arrange
		mockDep := new(Mock{{DepInterface}})
		input := {{HAPPY_PATH_INPUT}}
		expected := {{EXPECTED_OUTPUT}}
		mockDep.On("{{DepMethod}}", mock.Anything, input).Return({{DEP_RETURN_VALUE}}, nil)

		svc := {{package_name}}.New{{ClassName}}(mockDep)

		// Act
		result, err := svc.{{MethodName}}(context.Background(), input)

		// Assert
		require.NoError(t, err)
		assert.Equal(t, expected, result)
		mockDep.AssertExpectations(t)
	})

	t.Run("edge case — {{EDGE_CASE_1_DESCRIPTION}} with empty input", func(t *testing.T) {
		// Arrange
		mockDep := new(Mock{{DepInterface}})
		emptyInput := {{EDGE_CASE_1_INPUT}}
		mockDep.On("{{DepMethod}}", mock.Anything, emptyInput).Return({{EDGE_CASE_1_DEP_RETURN}}, nil)

		svc := {{package_name}}.New{{ClassName}}(mockDep)

		// Act
		result, err := svc.{{MethodName}}(context.Background(), emptyInput)

		// Assert
		require.NoError(t, err)
		assert.Equal(t, {{EDGE_CASE_1_EXPECTED}}, result)
	})

	t.Run("edge case — {{EDGE_CASE_2_DESCRIPTION}} at boundary", func(t *testing.T) {
		// Arrange
		mockDep := new(Mock{{DepInterface}})
		boundaryInput := {{EDGE_CASE_2_INPUT}}
		mockDep.On("{{DepMethod}}", mock.Anything, mock.Anything).Return({{EDGE_CASE_2_DEP_RETURN}}, nil)

		svc := {{package_name}}.New{{ClassName}}(mockDep)

		// Act
		result, err := svc.{{MethodName}}(context.Background(), boundaryInput)

		// Assert
		require.NoError(t, err)
		assert.NotNil(t, result)
	})

	t.Run("negative path — {{NEGATIVE_CONDITION}}", func(t *testing.T) {
		// Arrange
		mockDep := new(Mock{{DepInterface}})
		mockDep.On("{{DepMethod}}", mock.Anything, mock.Anything).
			Return({{ZERO_VALUE}}, errors.New("{{ERROR_MESSAGE}}"))

		svc := {{package_name}}.New{{ClassName}}(mockDep)

		// Act
		_, err := svc.{{MethodName}}(context.Background(), {{INVALID_INPUT}})

		// Assert
		require.Error(t, err)
		assert.Contains(t, err.Error(), "{{ERROR_MESSAGE}}")
		mockDep.AssertExpectations(t)
	})

	t.Run("negative path — context cancelled", func(t *testing.T) {
		// Arrange
		mockDep := new(Mock{{DepInterface}})
		ctx, cancel := context.WithCancel(context.Background())
		cancel() // cancelled immediately

		svc := {{package_name}}.New{{ClassName}}(mockDep)

		// Act
		_, err := svc.{{MethodName}}(ctx, {{HAPPY_PATH_INPUT}})

		// Assert
		require.Error(t, err)
		assert.ErrorIs(t, err, context.Canceled)
	})
}

// ─── Table-driven tests (use for functions with many input variants) ──────────

func Test{{FunctionName}}TableDriven(t *testing.T) {
	tests := []struct {
		name        string
		input       {{InputType}}
		depReturn   {{ReturnType}}
		depErr      error
		wantResult  {{ReturnType}}
		wantErr     bool
	}{
		{
			name:       "valid input returns expected",
			input:      {{HAPPY_PATH_INPUT}},
			depReturn:  {{DEP_RETURN_VALUE}},
			wantResult: {{EXPECTED_OUTPUT}},
		},
		{
			name:    "dep error propagates",
			input:   {{HAPPY_PATH_INPUT}},
			depErr:  errors.New("db error"),
			wantErr: true,
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			// Arrange
			mockDep := new(Mock{{DepInterface}})
			mockDep.On("{{DepMethod}}", mock.Anything, mock.Anything).
				Return(tc.depReturn, tc.depErr)

			svc := {{package_name}}.New{{ClassName}}(mockDep)

			// Act
			result, err := svc.{{MethodName}}(context.Background(), tc.input)

			// Assert
			if tc.wantErr {
				require.Error(t, err)
			} else {
				require.NoError(t, err)
				assert.Equal(t, tc.wantResult, result)
			}
		})
	}
}
